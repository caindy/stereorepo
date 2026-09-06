#![doc = include_str!("../README.md")]

use std::collections::HashSet;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, ExitCode};

/// What one gate step reports. Three outcomes, never two: a step that cannot
/// run is not a step that passed, and it is not a step that failed either.
#[derive(Debug, PartialEq, Eq)]
pub enum Outcome {
    /// The step did not run. Reported loudly, unmarked, and not a failure —
    /// a missing tool is an absence of evidence, and exiting non-zero for it
    /// would train the reflex of installing nothing and skipping the step.
    CouldNotRun(String),
    /// The step ran and found nothing. Carries what it checked, so the mark is
    /// a claim about scope and not a bare tick.
    Passed(String),
    /// The step found something. One line per problem, each naming where.
    Found(Vec<String>),
}

impl Outcome {
    /// Whether this outcome fails the gate.
    #[must_use]
    pub fn failed(&self) -> bool {
        matches!(self, Outcome::Found(_))
    }

    /// Prints the outcome in the one shape every gate prints — A21: `ok`, `x`
    /// or `?`, the step, then what it covered, found, or could not do — so a
    /// reader of any Project's gate reads every other's.
    pub fn report(&self, label: &str) {
        print!("{}", self.rendered(label));
    }

    /// The report as text: `?` unmarked, `ok` with its scope, `x` with a count
    /// and one indented line per problem.
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

/// A gate step: a label somebody types after `cargo xtask`, and what it runs.
pub type Step = (&'static str, fn(&Path) -> Outcome);

/// Every step, in the order the gate runs them. Cheap and pure first, so a
/// formatting slip is reported before a build is paid for.
pub const STEPS: &[Step] = &[
    ("fmt", fmt),
    ("lints", lints),
    ("clippy", clippy),
    ("doc", doc),
    ("test", test),
    ("orphans", orphans),
    ("receipts", receipts),
    ("mutants", mutants),
];

/// The steps a word selects: every step for `gate`, the one step with that
/// label otherwise, and nothing for a word that is neither. Built on `find`
/// rather than `filter` on purpose: a word other than `gate` can select one
/// step at most, however this is changed, so a test that runs the binary with
/// one word can never be made to run the whole gate — and the gate's `test`
/// step runs the tests, so that would be the gate inside itself.
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

/// Runs the steps and reports each. No steps is a usage error, exit 2. The
/// binary is `select` then this and nothing else, so that every branch here is
/// reached by a test in-process.
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

/// Runs one cargo subcommand as a step. Output streams through, so what the
/// tool found is on the screen above the line that says it found something.
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

/// `cargo fmt --check`. Never `cargo fmt`: a gate step that rewrites the tree
/// leaves the author unsure what they committed.
#[must_use]
pub fn fmt(root: &Path) -> Outcome {
    cargo(
        root,
        &["fmt", "--all", "--check"],
        &[],
        "every source file, and none of them rewritten",
    )
}

/// `cargo clippy` with every warning an error, over every target so tests and
/// the xtask are held to the same standard as the library.
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

/// `cargo doc` with every rustdoc warning an error. With `missing_docs` denied
/// in the workspace lints, no public item goes undocumented and no broken
/// intra-doc link survives.
#[must_use]
pub fn doc(root: &Path) -> Outcome {
    cargo(
        root,
        &["doc", "--workspace", "--no-deps"],
        &[("RUSTDOCFLAGS", "-D warnings")],
        "every public item documented, every intra-doc link resolving",
    )
}

/// `cargo test`, which runs the doctests too — the examples in the prose are
/// executed, not asserted.
#[must_use]
pub fn test(root: &Path) -> Outcome {
    cargo(
        root,
        &["test", "--workspace"],
        &[],
        "every test and every doctest",
    )
}

/// `cargo mutants`: the signal behind the tests. A test that passes against
/// broken code passed for the wrong reason, and this is how that is found.
/// Not installed is reported, not passed.
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

/// Whether `cargo <name> --version` answers, which is how a cargo extension
/// says it is installed.
#[must_use]
pub fn subcommand_present(root: &Path, name: &str) -> bool {
    Command::new("cargo")
        .args([name, "--version"])
        .current_dir(root)
        .output()
        .is_ok_and(|out| out.status.success())
}

/// Every markdown file under a package is included by a source file in it.
///
/// Prose beside code that nothing includes is a second copy waiting to drift
/// — or a first copy nobody reads, which is debris. Either way it is an
/// orphan. A missing include fails the build already; this holds the other
/// direction.
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

/// Every entry in a history log names a test that exists.
///
/// An entry's receipt is the test that would fail if the change were undone.
/// That makes relevance mechanical: if the test is gone, the entry is stale.
/// The tests are read from `cargo test -- --list`, so what is checked is what
/// would actually run.
#[must_use]
pub fn receipts(root: &Path) -> Outcome {
    match listed_tests(root) {
        Ok(tests) => receipts_against(root, &tests),
        Err(why) => Outcome::CouldNotRun(why),
    }
}

/// [`receipts`], given the tests. Separated so a probe can hand it a list.
#[must_use]
pub fn receipts_against(root: &Path, tests: &[String]) -> Outcome {
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
                match entry.receipt {
                    None => problems.push(format!("{name}: '{}' names no receipt", entry.title)),
                    Some(receipt) if !tests.iter().any(|test| test == &receipt) => {
                        problems.push(format!(
                            "{name}: '{}' names `{receipt}`, which no test reports",
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

/// No lint is switched off in configuration.
///
/// An `allow` in a `[lints]` table, or a `-A` in a cargo config's rustflags,
/// is a rule deleted where nobody reads. The site is the only place a
/// suppression is legible, and there it carries a reason.
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

/// One entry of a history log: its heading, and the receipt it names.
struct Entry {
    title: String,
    receipt: Option<String>,
}

/// The entries of a history log. An entry starts at a `###` heading; its
/// receipt is a line starting `Receipt:` naming a test in backticks. HTML
/// comments are not entries, which is how a log can carry the form of one.
fn entries_of(text: &str) -> Vec<Entry> {
    let mut entries: Vec<Entry> = Vec::new();
    for line in without_comments(text).lines() {
        if let Some(title) = line.strip_prefix("### ") {
            entries.push(Entry {
                title: title.trim().to_owned(),
                receipt: None,
            });
        } else if let Some(rest) = line.trim().strip_prefix("Receipt:")
            && let Some(entry) = entries.last_mut()
        {
            entry.receipt = rest.split('`').nth(1).map(str::to_owned);
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
