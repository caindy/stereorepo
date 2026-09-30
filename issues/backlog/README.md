# backlog

The queue. The pair loop takes the first ripe Issue in running order: the slugs `ORDER` names, one per line (the developer's above `# groomed below`, grooming's below it), then the rest in filename order. An Issue is ripe when its `waits_on` Issues are all done and it has no `Needs elaboration` section. The loop sends an Issue back here, with that section, when it cannot be done as written.
