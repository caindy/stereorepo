# History

### A program's library body kept the channel a previous probe had loaded, and wrote to GitHub

Every probe loads the channel afresh and stands its fakes in on that copy, and
a program loaded through the channel's own `sibling()` binds the copy that
loaded it. A library package the program is the entry of does not: `lib.move`
is imported once, cached in `sys.modules`, and bound to the channel of whichever
probe imported it first. Every later probe stood its fakes in on a channel the
package never saw, and the package reached GitHub through the coder's
credential. The first gate run over the split of `move` filed three Challenges
on this repository, solorepo's #815, #816 and #817, before the cause was found.
Established: the loader evicts the library body of every program the table
names from `sys.modules` before it loads the channel, so the package binds the
copy the probe stands its fakes in on; a package split from another program
is covered by its name in the table and needs nothing added here.

Evidence: `.meta/checks/probes/harness/loaders.py::load_channel`
