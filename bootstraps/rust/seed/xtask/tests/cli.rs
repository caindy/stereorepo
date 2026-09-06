//! The binary: which steps a word selects, and what an unknown word gets.

use std::process::Command;

fn xtask(arg: &str) -> (i32, String, String) {
    let out = Command::new(env!("CARGO_BIN_EXE_xtask"))
        .arg(arg)
        .output()
        .unwrap();
    (
        out.status.code().unwrap(),
        String::from_utf8_lossy(&out.stdout).into_owned(),
        String::from_utf8_lossy(&out.stderr).into_owned(),
    )
}

#[test]
fn an_unknown_step_is_usage() {
    let (code, stdout, stderr) = xtask("nonesuch");
    assert_eq!(code, 2);
    assert_eq!(stdout, "");
    assert!(
        stderr.starts_with("usage: cargo xtask [gate | fmt | lints |"),
        "{stderr}"
    );
}

#[test]
fn one_word_runs_one_step() {
    let (code, stdout, _) = xtask("lints");
    assert_eq!(code, 0, "{stdout}");
    assert_eq!(stdout.lines().count(), 1, "{stdout}");
    assert!(stdout.starts_with("ok lints — "), "{stdout}");
}
