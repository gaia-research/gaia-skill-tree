# Draft Queue

`docs/meta/drafts.json` holds post entries that have been written and rendered
but pulled off the live site before launch. It uses the exact same schema as
`docs/meta/posts.json` (`{"posts": [...]}`) so an entry can move back verbatim
whenever the founder is ready to relaunch it.

Nothing reads this file automatically — no script, no page. It exists purely
as a holding area so a finished post doesn't have to be re-authored later.

## Relaunching a draft

This is a rare, deliberate action — do it by hand, not with a script:

1. Cut the post object out of `docs/meta/drafts.json`'s `posts` array.
2. Paste it into `docs/meta/posts.json`'s `posts` array (position determines
   sort order — the array is newest-first, so place it where its `date`
   belongs, or move it to the top and bump `date` if relaunching "fresh").
3. Re-run the queue/hero patch so `docs/index.html` and `docs/meta.html`
   pick up the change:

   ```
   python3 -c "
   import sys; sys.path.insert(0, 'scripts')
   from add_post import load_posts, save_posts, patch_index, patch_meta_html
   posts = load_posts()
   # posts.json already has the relaunched entry from step 2 — just re-patch
   hero = next((p for p in posts if p.get('type') == 'report'), None)
   patch_index(posts, hero_url=hero['url'] if hero else None, hero_label=hero['label'] if hero else None)
   patch_meta_html(posts)
   "
   ```

4. Remove the entry from `docs/meta/drafts.json` (it now lives only in
   `posts.json`).
5. Leave the rendered report HTML and markdown source where they already are
   under `docs/meta/reports/` and `docs/meta/` — they were never moved.
