//! Each pure step watched failing, against a tree built to fail it, and then
//! watched passing against the same tree put right. A guardrail never observed
//! to fail is not evidence of anything.

use std::fs;
use std::path::{Path, PathBuf};

use std::process::ExitCode;

use xtask::{Outcome, Step, fmt, lints, orphans, receipts, receipts_against, run};

/// A throwaway package under the target directory, so probes leave nothing
/// behind that the orphan check would then find. Its manifest carries an empty
/// `[workspace]` so cargo does not mistake it for a member of this one.
struct Tree(PathBuf);

const MANIFEST: &str =
    "[package]\nname = \"probe\"\nversion = \"0.0.0\"\nedition = \"2024\"\n\n[workspace]\n";

impl Tree {
    fn new(name: &str) -> Self {
        let root = Path::new(env!("CARGO_TARGET_TMPDIR")).join(name);
        let _ = fs::remove_dir_all(&root);
        fs::create_dir_all(root.join("src")).unwrap();
        fs::write(root.join("Cargo.toml"), MANIFEST).unwrap();
        fs::write(
            root.join("src/lib.rs"),
            "#![doc = include_str!(\"../README.md\")]\n",
        )
        .unwrap();
        fs::write(root.join("README.md"), "The probe crate.\n").unwrap();
        Self(root)
    }

    fn write(&self, path: &str, text: &str) -> &Self {
        let full = self.0.join(path);
        fs::create_dir_all(full.parent().unwrap()).unwrap();
        fs::write(full, text).unwrap();
        self
    }
}

impl Drop for Tree {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

fn found(outcome: Outcome) -> Vec<String> {
    match outcome {
        Outcome::Found(problems) => problems,
        other => panic!("expected a finding, got {other:?}"),
    }
}

fn passed(outcome: Outcome) -> String {
    match outcome {
        Outcome::Passed(scope) => scope,
        other => panic!("expected a pass, got {other:?}"),
    }
}

#[test]
fn a_markdown_file_nothing_includes_is_an_orphan() {
    let tree = Tree::new("orphan");
    assert_eq!(
        passed(orphans(&tree.0)),
        "1 markdown files under 1 packages, each included by a source file"
    );

    tree.write("src/stray.md", "Nothing includes this.\n");
    let problems = found(orphans(&tree.0));
    assert_eq!(problems.len(), 1);
    assert!(problems[0].contains("src/stray.md"), "{problems:?}");

    tree.write(
        "src/lib.rs",
        "#![doc = include_str!(\"../README.md\")]\n#![doc = include_str!(\"stray.md\")]\n",
    );
    assert_eq!(
        passed(orphans(&tree.0)),
        "2 markdown files under 1 packages, each included by a source file"
    );
}

#[test]
fn two_includes_on_one_line_both_count() {
    let tree = Tree::new("adjacent");
    tree.write("src/a.md", "a\n")
        .write("src/b.md", "b\n")
        .write(
            "src/lib.rs",
            "#![doc = include_str!(\"../README.md\")]\n#![doc = concat!(include_str!(\"a.md\"),include_str!(\"b.md\"))]\n",
        );
    assert_eq!(
        passed(orphans(&tree.0)),
        "3 markdown files under 1 packages, each included by a source file"
    );
}

#[test]
fn build_output_and_hidden_directories_are_not_looked_at() {
    let tree = Tree::new("skipped");
    tree.write("target/doc/stray.md", "rustdoc output\n")
        .write("mutants.out/stray.md", "mutants output\n")
        .write(".hidden/stray.md", "hidden\n")
        .write("target/Cargo.toml", "[package]\nname = \"not-a-package\"\n");
    assert_eq!(
        passed(orphans(&tree.0)),
        "1 markdown files under 1 packages, each included by a source file"
    );
}

#[test]
fn a_history_entry_names_a_test_that_exists() {
    let tree = Tree::new("receipt");
    let tests = vec!["example::tests::holds".to_owned()];
    tree.write(
        "src/lib.rs",
        "#![doc = include_str!(\"../README.md\")]\n#![doc = include_str!(\"lib.history.md\")]\n",
    );

    tree.write(
        "src/lib.history.md",
        "# History\n\n### Something failed\n\nEstablished: a thing.\n",
    );
    let problems = found(receipts_against(&tree.0, &tests));
    assert_eq!(problems.len(), 1);
    assert!(
        problems[0].contains("'Something failed' names no receipt"),
        "{problems:?}"
    );

    tree.write(
        "src/lib.history.md",
        "# History\n\n### Something failed\n\nEstablished: a thing.\n\nReceipt: `example::tests::gone`\n",
    );
    let problems = found(receipts_against(&tree.0, &tests));
    assert!(
        problems[0].contains("`example::tests::gone`, which no test reports"),
        "{problems:?}"
    );

    tree.write(
        "src/lib.history.md",
        "# History\n\n### Something failed\n\nEstablished: a thing.\n\nReceipt: `example::tests::holds`\n\n### And again\n\nReceipt: `example::tests::holds`\n",
    );
    assert_eq!(
        passed(receipts_against(&tree.0, &tests)),
        "2 entries across 1 history logs, each naming a test that exists"
    );
}

#[test]
fn the_form_of_an_entry_in_a_comment_is_not_an_entry() {
    let tree = Tree::new("comment");
    tree.write(
        "src/lib.history.md",
        "# History\n\n<!--\n### <what failed>\n\nReceipt: `example::tests::<name>`\n-->\n\n### Real\n\nReceipt: `t::real`\n",
    );
    assert_eq!(
        passed(receipts_against(&tree.0, &["t::real".to_owned()])),
        "1 entries across 1 history logs, each naming a test that exists"
    );
    let problems = found(receipts_against(&tree.0, &[]));
    assert_eq!(problems.len(), 1, "{problems:?}");
    assert!(problems[0].contains("'Real'"), "{problems:?}");
}

#[test]
fn receipts_are_checked_against_the_tests_cargo_would_run() {
    let tree = Tree::new("listed");
    tree.write(
        "src/lib.rs",
        "#![doc = include_str!(\"../README.md\")]\n#![doc = include_str!(\"lib.history.md\")]\n\n#[cfg(test)]\nmod tests {\n    #[test]\n    fn holds() {}\n}\n",
    );
    tree.write(
        "src/lib.history.md",
        "# History\n\n### Real\n\nReceipt: `tests::holds`\n",
    );
    assert_eq!(
        passed(receipts(&tree.0)),
        "1 entries across 1 history logs, each naming a test that exists"
    );

    tree.write(
        "src/lib.history.md",
        "# History\n\n### Stale\n\nReceipt: `tests::gone`\n",
    );
    let problems = found(receipts(&tree.0));
    assert!(
        problems[0].contains("`tests::gone`, which no test reports"),
        "{problems:?}"
    );

    tree.write("src/lib.rs", "this does not compile\n");
    assert!(matches!(receipts(&tree.0), Outcome::CouldNotRun(ref why) if why.contains("--list")));
}

#[test]
fn a_lint_allowed_in_configuration_is_found() {
    let tree = Tree::new("lints");
    assert_eq!(
        passed(lints(&tree.0)),
        "1 manifests and 0 cargo configs, no lint switched off in configuration"
    );

    for header in [
        "[lints]",
        "[lints.clippy]",
        "[workspace.lints]",
        "[workspace.lints.rust]",
    ] {
        tree.write(
            "Cargo.toml",
            &format!("{MANIFEST}\n{header}\ntoo_many_lines = \"allow\"\n"),
        );
        let problems = found(lints(&tree.0));
        assert_eq!(problems.len(), 1, "{header}: {problems:?}");
        assert!(
            problems[0].contains("Cargo.toml:9"),
            "{header}: {problems:?}"
        );
    }

    tree.write(
        "Cargo.toml",
        &format!(
            "{MANIFEST}\n[lints.clippy]\npedantic = \"warn\"\n\n[dependencies]\nallow = \"1\"\n"
        ),
    );
    assert!(
        matches!(lints(&tree.0), Outcome::Passed(_)),
        "allow outside a lints table is not a suppression"
    );

    tree.write(
        "Cargo.toml",
        &format!("{MANIFEST}\n[lints.clippy]\n# was \"allow\" once\npedantic = \"warn\"\n"),
    );
    assert!(
        matches!(lints(&tree.0), Outcome::Passed(_)),
        "a comment is not a suppression"
    );

    tree.write(
        ".cargo/config.toml",
        "[alias]\nx = \"run -- --allow\"\n[build]\nrustflags = [\"-A\", \"dead_code\"]\n",
    );
    let problems = found(lints(&tree.0));
    assert_eq!(problems.len(), 1, "{problems:?}");
    assert!(problems[0].contains(".cargo/config.toml:4"), "{problems:?}");
    assert_eq!(found(lints(&tree.0)).len(), 1);

    tree.write(
        ".cargo/config.toml",
        "[build]\nrustdocflags = [\"--cap-lints\", \"allow\"]\n",
    );
    assert!(found(lints(&tree.0))[0].contains("config.toml:2"));

    tree.write(
        ".cargo/config.toml",
        "[build]\nrustflags = [\"-D\", \"warnings\"]\n",
    );
    assert_eq!(
        passed(lints(&tree.0)),
        "1 manifests and 1 cargo configs, no lint switched off in configuration"
    );
}

#[test]
fn a_cargo_step_reports_what_cargo_found() {
    let tree = Tree::new("cargo");
    tree.write(
        "src/lib.rs",
        "#![doc = include_str!(\"../README.md\")]\n\npub fn f() {}\n",
    );
    assert_eq!(
        passed(fmt(&tree.0)),
        "every source file, and none of them rewritten"
    );

    tree.write(
        "src/lib.rs",
        "#![doc = include_str!(\"../README.md\")]\n\npub fn f( ) {  }\n",
    );
    let problems = found(fmt(&tree.0));
    assert_eq!(
        problems,
        ["`cargo fmt --all --check` exited with exit status: 1"]
    );
}

#[test]
fn a_run_fails_when_any_step_finds_something() {
    let tree = Tree::new("run");
    let ok = format!("{:?}", ExitCode::SUCCESS);
    let failure = format!("{:?}", ExitCode::FAILURE);
    let both: [&Step; 2] = [&("lints", lints), &("orphans", orphans)];
    assert_eq!(format!("{:?}", run(&tree.0, &both)), ok);

    tree.write(
        "Cargo.toml",
        &format!("{MANIFEST}\n[lints.rust]\ndead_code = \"allow\"\n"),
    );
    assert_eq!(format!("{:?}", run(&tree.0, &both)), failure);
    assert_eq!(
        format!("{:?}", run(&tree.0, &[&("orphans", orphans)])),
        ok,
        "one step's finding is not another's"
    );
}
