#![doc = include_str!("../README.md")]

use std::collections::HashSet;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, ExitCode};

/// Represents the result of a gate step execution adhering to Article 6.
#[derive(Debug, PartialEq, Eq)]
pub enum Outcome {
    /// The step did not run due to missing tools or environmental prerequisites.
    CouldNotRun(String),
    /// The step ran and found zero defects, recording verified scope.
    Passed(String),
    /// The step detected one or more defects, recording diagnostic descriptions.
    Found(Vec<String>),
}

impl Outcome {
    /// Checks whether this outcome represents a failing gate result.
    #[must_use]
    pub fn failed(&self) -> bool {
        matches!(self, Outcome::Found(_))
    }

    /// Prints the rendered outcome to standard output.
    pub fn report(&self, label: &str) {
        print!("{}", self.rendered(label));
    }

    /// Formats the outcome into a standardized gate report line adhering to Article 21.
    #[must_use]
    pub fn rendered(&self, label: &str) -> String {
        match self {
            Outcome::CouldNotRun(why) => format!("?  {label}: {why}\n"),
            Outcome::Passed(scope) => format!("ok {label} — {scope}\n"),
            Outcome::Found(problems) => {
                let mut out = format!("x  {label} ({})\n", problems.len());
                for problem in problems {
                    out.push_str("     ");
                    out.push_str(problem);
                    out.push('\n');
                }
                out
            }
        }
    }
}

/// A named gate step associating a command-line label with an execution function.
pub type Step = (&'static str, fn(&Path) -> Outcome);

/// Ordered sequence of gate steps executed by the gate runner.
pub const STEPS: &[Step] = &[
    ("fmt", fmt),
    ("lints", lints),
    ("clippy", clippy),
    ("doc", doc),
    ("test", test),
    ("orphans", orphans),
    ("evidence", evidence),
    ("mutants", mutants),
];

/// Selects gate steps corresponding to a command-line label.
///
/// Returns all steps when `wanted` is `"gate"`, or a single matching step if found.
#[must_use]
pub fn select(wanted: &str) -> Vec<&'static Step> {
    match wanted {
        "gate" => STEPS.iter().collect(),
        label => STEPS
            .iter()
            .find(|(known, _)| *known == label)
            .into_iter()
            .collect(),
    }
}

/// Executes each step in sequence and prints its formatted outcome.
///
/// Returns `ExitCode::SUCCESS` if all steps pass, `ExitCode::FAILURE` if any step
/// finds issues, or exit code 2 if `steps` is empty.
#[must_use]
pub fn run(root: &Path, steps: &[&Step]) -> ExitCode {
    if steps.is_empty() {
        let known: Vec<_> = STEPS.iter().map(|(label, _)| *label).collect();
        eprintln!("usage: cargo xtask [gate | {}]", known.join(" | "));
        return ExitCode::from(2);
    }
    let mut failed = false;
    for (label, step) in steps {
        let outcome = step(root);
        outcome.report(label);
        failed |= outcome.failed();
    }
    if failed {
        ExitCode::FAILURE
    } else {
        ExitCode::SUCCESS
    }
}

/// Executes a cargo subcommand as a gate step subprocess.
fn cargo(root: &Path, args: &[&str], env: &[(&str, &str)], scope: &str) -> Outcome {
    let status = Command::new("cargo")
        .args(args)
        .envs(env.iter().copied())
        .current_dir(root)
        .status();
    match status {
        Err(error) => Outcome::CouldNotRun(format!("cargo did not start: {error}")),
        Ok(status) if status.success() => Outcome::Passed(scope.to_owned()),
        Ok(status) => Outcome::Found(vec![format!(
            "`cargo {}` exited with {status}",
            args.join(" ")
        )]),
    }
}

/// Runs `cargo fmt --all --check` across the workspace.
#[must_use]
pub fn fmt(root: &Path) -> Outcome {
    cargo(
        root,
        &["fmt", "--all", "--check"],
        &[],
        "every source file, and none of them rewritten",
    )
}

/// Runs `cargo clippy --workspace --all-targets -- -D warnings` across the workspace.
#[must_use]
pub fn clippy(root: &Path) -> Outcome {
    cargo(
        root,
        &[
            "clippy",
            "--workspace",
            "--all-targets",
            "--",
            "-D",
            "warnings",
        ],
        &[],
        "every target, with every warning an error",
    )
}

/// Runs `cargo doc --workspace --no-deps` with rustdoc warnings treated as errors.
#[must_use]
pub fn doc(root: &Path) -> Outcome {
    cargo(
        root,
        &["doc", "--workspace", "--no-deps"],
        &[("RUSTDOCFLAGS", "-D warnings")],
        "every public item documented, every intra-doc link resolving",
    )
}

/// Runs `cargo test --workspace` including documentation tests.
#[must_use]
pub fn test(root: &Path) -> Outcome {
    cargo(
        root,
        &["test", "--workspace"],
        &[],
        "every test and every doctest",
    )
}

/// Runs `cargo mutants --no-shuffle` across the workspace if installed.
#[must_use]
pub fn mutants(root: &Path) -> Outcome {
    if subcommand_present(root, "mutants") {
        cargo(
            root,
            &["mutants", "--no-shuffle"],
            &[],
            "every viable mutant caught by a test",
        )
    } else {
        Outcome::CouldNotRun(
            "cargo-mutants is not installed, so the signal behind the tests did not run; \
             `cargo install cargo-mutants --locked`"
                .to_owned(),
        )
    }
}

/// Checks whether a specified cargo subcommand is installed and available on PATH.
#[must_use]
pub fn subcommand_present(root: &Path, name: &str) -> bool {
    Command::new("cargo")
        .args([name, "--version"])
        .current_dir(root)
        .output()
        .is_ok_and(|out| out.status.success())
}

/// Verifies that every markdown document in a package is included by a Rust source file.
#[must_use]
pub fn orphans(root: &Path) -> Outcome {
    let packages = packages(root);
    let mut problems = Vec::new();
    let mut counted = 0;
    for package in &packages {
        let included: HashSet<PathBuf> = files(package, "rs")
            .iter()
            .flat_map(|source| includes(source))
            .collect();
        for markdown in files(package, "md") {
            counted += 1;
            let resolved = markdown.canonicalize().unwrap_or(markdown.clone());
            if !included.contains(&resolved) {
                problems.push(format!(
                    "{}: included by nothing",
                    relative(root, &markdown)
                ));
            }
        }
    }
    if problems.is_empty() {
        Outcome::Passed(format!(
            "{counted} markdown files under {} packages, each included by a source file",
            packages.len()
        ))
    } else {
        Outcome::Found(problems)
    }
}

/// Verifies that every history log entry names an existing test in the test suite.
#[must_use]
pub fn evidence(root: &Path) -> Outcome {
    match listed_tests(root) {
        Ok(tests) => evidence_against(root, &tests),
        Err(why) => Outcome::CouldNotRun(why),
    }
}

/// Verifies history log evidence entries against a list of collected test names.
#[must_use]
pub fn evidence_against(root: &Path, tests: &[String]) -> Outcome {
    let mut problems = Vec::new();
    let mut logs = 0;
    let mut entries = 0;
    for package in packages(root) {
        for log in files(&package, "md")
            .into_iter()
            .filter(|path| path.to_string_lossy().ends_with(".history.md"))
        {
            logs += 1;
            let text = fs::read_to_string(&log).unwrap_or_default();
            for entry in entries_of(&text) {
                entries += 1;
                let name = relative(root, &log);
                match entry.evidence {
                    None => problems.push(format!("{name}: '{}' names no evidence", entry.title)),
                    Some(evidence) if !tests.iter().any(|test| test == &evidence) => {
                        problems.push(format!(
                            "{name}: '{}' names `{evidence}`, which no test reports",
                            entry.title
                        ));
                    }
                    Some(_) => {}
                }
            }
        }
    }
    if problems.is_empty() {
        Outcome::Passed(format!(
            "{entries} entries across {logs} history logs, each naming a test that exists"
        ))
    } else {
        Outcome::Found(problems)
    }
}

/// Verifies that manifests and cargo configs do not disable lints in configuration.
#[must_use]
pub fn lints(root: &Path) -> Outcome {
    let mut problems = Vec::new();
    let manifests = files(root, "toml")
        .into_iter()
        .filter(|path| path.file_name().is_some_and(|name| name == "Cargo.toml"))
        .collect::<Vec<_>>();
    for manifest in &manifests {
        let text = fs::read_to_string(manifest).unwrap_or_default();
        for (number, line) in allowed_in_manifest(&text) {
            problems.push(format!(
                "{}:{number}: `{line}` switches a lint off in configuration",
                relative(root, manifest)
            ));
        }
    }
    // `.cargo/` is hidden, and the walker skips hidden directories on purpose,
    // so the workspace's own config is named rather than found.
    let configs = [root.join(".cargo/config.toml"), root.join(".cargo/config")]
        .into_iter()
        .filter(|path| path.is_file())
        .collect::<Vec<_>>();
    for config in &configs {
        let text = fs::read_to_string(config).unwrap_or_default();
        for (number, line) in text.lines().enumerate() {
            let flags = line.contains("rustflags") || line.contains("rustdocflags");
            if flags
                && (line.contains("\"-A")
                    || line.contains("--allow")
                    || line.contains("--cap-lints"))
            {
                problems.push(format!(
                    "{}:{}: `{}` switches a lint off in configuration",
                    relative(root, config),
                    number + 1,
                    line.trim()
                ));
            }
        }
    }
    if problems.is_empty() {
        Outcome::Passed(format!(
            "{} manifests and {} cargo configs, no lint switched off in configuration",
            manifests.len(),
            configs.len()
        ))
    } else {
        Outcome::Found(problems)
    }
}

/// The lines of a manifest that set a lint to `allow`, inside a lints table.
fn allowed_in_manifest(text: &str) -> Vec<(usize, String)> {
    let mut in_lints = false;
    let mut found = Vec::new();
    for (index, raw) in text.lines().enumerate() {
        let line = raw.trim();
        if line.starts_with('[') {
            let header = line.trim_matches(|c| c == '[' || c == ']');
            in_lints = header == "lints"
                || header.starts_with("lints.")
                || header == "workspace.lints"
                || header.starts_with("workspace.lints.");
            continue;
        }
        let uncommented = line.split('#').next().unwrap_or("");
        if in_lints && uncommented.contains("\"allow\"") {
            found.push((index + 1, line.to_owned()));
        }
    }
    found
}

/// One entry of a history log: its heading, and the evidence it names.
struct Entry {
    title: String,
    evidence: Option<String>,
}

/// The entries of a history log. An entry starts at a `###` heading; its
/// evidence is a line starting `Evidence:` naming a test in backticks. HTML
/// comments are not entries, which is how a log can carry the form of one.
fn entries_of(text: &str) -> Vec<Entry> {
    let mut entries: Vec<Entry> = Vec::new();
    for line in without_comments(text).lines() {
        if let Some(title) = line.strip_prefix("### ") {
            entries.push(Entry {
                title: title.trim().to_owned(),
                evidence: None,
            });
        } else if let Some(rest) = line.trim().strip_prefix("Evidence:")
            && let Some(entry) = entries.last_mut()
        {
            entry.evidence = rest.split('`').nth(1).map(str::to_owned);
        }
    }
    entries
}

/// The text with every `<!-- … -->` removed. A comment never closed runs to
/// the end, as it does in HTML.
fn without_comments(text: &str) -> String {
    let mut pieces = text.split("<!--");
    let mut out = pieces.next().unwrap_or_default().to_owned();
    for piece in pieces {
        if let Some((_, after)) = piece.split_once("-->") {
            out.push_str(after);
        }
    }
    out
}

/// The tests `cargo test` would run, as `module::path::name`, one per line of
/// `--list` that ends in `: test`.
fn listed_tests(root: &Path) -> Result<Vec<String>, String> {
    let output = Command::new("cargo")
        .args(["test", "--workspace", "--", "--list"])
        .current_dir(root)
        .output()
        .map_err(|error| format!("cargo did not start: {error}"))?;
    if !output.status.success() {
        return Err(format!(
            "`cargo test -- --list` exited with {}",
            output.status
        ));
    }
    Ok(String::from_utf8_lossy(&output.stdout)
        .lines()
        .filter_map(|line| line.strip_suffix(": test"))
        .map(str::to_owned)
        .collect())
}

/// The paths named by `include_str!("…")` in a source file, resolved the way
/// the compiler resolves them: relative to the file that includes them.
fn includes(source: &Path) -> Vec<PathBuf> {
    let text = fs::read_to_string(source).unwrap_or_default();
    let base = source.parent().unwrap_or(Path::new("."));
    text.split("include_str!")
        .skip(1)
        .filter_map(|after| after.split('"').nth(1))
        .map(|literal| {
            let path = base.join(literal);
            path.canonicalize().unwrap_or(path)
        })
        .collect()
}

/// The directories under `root` holding a `Cargo.toml` with a `[package]`
/// table — the packages, as against the workspace's virtual manifest.
fn packages(root: &Path) -> Vec<PathBuf> {
    files(root, "toml")
        .into_iter()
        .filter(|path| path.file_name().is_some_and(|name| name == "Cargo.toml"))
        .filter(|path| {
            fs::read_to_string(path)
                .unwrap_or_default()
                .contains("[package]")
        })
        .filter_map(|path| path.parent().map(Path::to_path_buf))
        .collect()
}

/// Every file under `dir` with the extension, skipping build output and
/// anything hidden.
fn files(dir: &Path, extension: &str) -> Vec<PathBuf> {
    let mut found = Vec::new();
    let mut pending = vec![dir.to_path_buf()];
    while let Some(current) = pending.pop() {
        let Ok(entries) = fs::read_dir(&current) else {
            continue;
        };
        for entry in entries.flatten() {
            let path = entry.path();
            let name = entry.file_name().to_string_lossy().into_owned();
            if path.is_dir() {
                if name != "target" && !name.starts_with('.') && !name.starts_with("mutants.out") {
                    pending.push(path);
                }
            } else if path.extension().is_some_and(|ext| ext == extension) {
                found.push(path);
            }
        }
    }
    found.sort();
    found
}

fn relative(root: &Path, path: &Path) -> String {
    let root = root.canonicalize().unwrap_or(root.to_path_buf());
    let path = path.canonicalize().unwrap_or(path.to_path_buf());
    path.strip_prefix(&root)
        .unwrap_or(&path)
        .to_string_lossy()
        .into_owned()
}

#[cfg(test)]
mod tests {
    use super::{Outcome, STEPS, run, select, subcommand_present, without_comments};
    use std::path::Path;
    use std::process::ExitCode;

    fn labels(steps: &[&super::Step]) -> Vec<&'static str> {
        steps.iter().map(|(label, _)| *label).collect()
    }

    #[test]
    fn gate_selects_every_step_and_a_word_selects_its_one() {
        assert_eq!(
            labels(&select("gate")),
            labels(&STEPS.iter().collect::<Vec<_>>())
        );
        assert_eq!(labels(&select("lints")), ["lints"]);
        assert_eq!(labels(&select("mutants")), ["mutants"]);
        assert!(select("nonesuch").is_empty());
    }

    #[test]
    fn a_subcommand_is_present_when_it_answers_version() {
        assert!(subcommand_present(Path::new("."), "clippy"));
        assert!(!subcommand_present(Path::new("."), "nonesuch"));
    }

    #[test]
    fn comments_are_removed_and_the_rest_kept_in_order() {
        assert_eq!(without_comments("a<!-- x -->b<!--y-->c"), "abc");
        assert_eq!(without_comments("a<!-- never closed"), "a");
        assert_eq!(without_comments("no comment"), "no comment");
    }

    #[test]
    fn no_steps_is_usage() {
        assert_eq!(
            format!("{:?}", run(Path::new("."), &[])),
            format!("{:?}", ExitCode::from(2))
        );
    }

    #[test]
    fn only_a_finding_fails() {
        assert!(!Outcome::CouldNotRun("no tool".into()).failed());
        assert!(!Outcome::Passed("everything".into()).failed());
        assert!(Outcome::Found(vec!["one".into()]).failed());
    }

    #[test]
    fn a_report_says_which_outcome_and_what_was_covered() {
        assert_eq!(
            Outcome::CouldNotRun("no tool".into()).rendered("step"),
            "?  step: no tool\n"
        );
        assert_eq!(
            Outcome::Passed("3 files".into()).rendered("step"),
            "ok step — 3 files\n"
        );
        assert_eq!(
            Outcome::Found(vec!["a".into(), "b".into()]).rendered("step"),
            "x  step (2)\n     a\n     b\n"
        );
    }
}
