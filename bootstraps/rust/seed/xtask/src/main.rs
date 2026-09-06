//! `cargo xtask gate` runs every step; `cargo xtask <step>` runs one. The
//! steps, what they hold, and the selection are all the library's.

use std::path::Path;
use std::process::ExitCode;

fn main() -> ExitCode {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .expect("xtask lives one level under the workspace root");
    let wanted = std::env::args().nth(1).unwrap_or_else(|| "gate".to_owned());
    xtask::run(root, &xtask::select(&wanted))
}
