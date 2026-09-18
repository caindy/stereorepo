"""The command line of `.meta/wikisplain.py`: check, scaffold, or verify a concept page.
"""
from __future__ import annotations

import argparse

from lib.wikisplain import ROOT, duplicates, lead, pages


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for wikisplain operational authoring tool (solorepo's DR-187)."""
    parser = argparse.ArgumentParser(
        description="Scaffold, check, and explain Knowledge Management wiki concepts (solorepo's DR-187)."
    )
    parser.add_argument(
        "concept",
        nargs="+",
        help="The name or title of the concept (e.g., 'Domain Storytelling').",
    )
    parser.add_argument(
        "--context",
        default="solorepo",
        help="The Bounded Context subfolder under wiki/ (default: 'solorepo').",
    )
    parser.add_argument(
        "--definition",
        default="",
        help="Copular definition sentence body (e.g. 'a visual modeling method...').",
    )
    parser.add_argument(
        "--synonyms",
        default="",
        help="Comma-separated synonyms or alternate labels.",
    )
    parser.add_argument(
        "--slug",
        default="",
        help="Slug to file the page under, naming both the file and the slug it declares (default: slugified title).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the generated page to stdout without writing to disk.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing wiki page if a duplicate exists.",
    )
    parser.add_argument(
        "--check-duplicate",
        action="store_true",
        help="Only check whether concept or slug already exists, then exit.",
    )

    args = parser.parse_args(argv)
    root = ROOT
    concept = " ".join(args.concept).strip()

    dups = duplicates.find_duplicates(concept, context=args.context, root=root)

    if args.check_duplicate:
        if dups:
            print(f"Collision: concept '{concept}' already exists in:")
            for d in dups:
                print(f"  - [{d['source']}] {d['label']} ({d['id']}) in {d['path']}: {d['details']}")
            return 1
        print(f"Clear: concept '{concept}' does not collide with vocabulary or wiki entities.")
        return 0

    if dups and not args.force:
        print(f"Error: concept '{concept}' collides with existing entities:")
        for d in dups:
            print(f"  - [{d['source']}] {d['label']} ({d['id']}) in {d['path']}: {d['details']}")
        print("Pass --force to proceed with scaffolding anyway.")
        return 1

    title = concept
    slug = args.slug.strip() or lead.slugify(title)
    syn_list = [s.strip() for s in args.synonyms.split(",") if s.strip()] if args.synonyms else []

    content = pages.generate_page(
        pages.Page(title=title, slug=slug, context=args.context,
                   definition=args.definition, synonyms=syn_list),
        root=root,
    )

    target_file = root / "wiki" / args.context / f"{slug}.md"
    rel_path = f"wiki/{args.context}/{slug}.md"

    problems = pages.verify_page(content, rel_path, root=root)
    if problems:
        print(f"Verification warnings for {rel_path}:")
        for p in problems:
            print(f"  ! {p}")

    if args.dry_run:
        print(content)
        return 0

    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text(content, encoding="utf-8")
    print(f"Scaffolded {rel_path} successfully.")
    return 0
