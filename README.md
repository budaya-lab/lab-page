# Budaya Lab website

A small static site: Home, Projects, Papers, People, News and Join. Code, models, datasets and the lab wiki live elsewhere (GitHub, Hugging Face and your wiki tool); the site links out to them.

## Editing content

| To change… | Edit |
|---|---|
| People | `_data/people.yml` (photos go in `assets/img/people/`) |
| Projects | `_data/projects.yml` (images in `assets/img/projects/`) |
| Papers | `_data/papers.csv` (a Google Scholar CSV export: Authors, Title, Publication, Volume, Number, Pages, Year, Publisher) |
| News | `_data/news.yml` |
| Menu order | `_data/navigation.yml` |
| Lab name, address, email | `_config.yml` |
| GitHub, Hugging Face, data portal and wiki links | `external:` in `_config.yml` |
| Home page intro | `index.html` |
| Join / prospective students | `join/index.md` |
| Colours and fonts | `assets/css/style.css` (variables at the top) |

Each YAML file starts with a comment describing its fields. Placeholders are in `[square brackets]`.

Each project has a short `summary` (shown on the home page card and at the top of its section) and a longer `description` (Markdown) shown on the Projects page. All projects are on one page; link to one with `/projects/#<id>`, e.g. `/projects/#jawi`. An optional `link:` (project site, GitHub repo or Hugging Face collection) adds a button, labelled by `link_label`. Setting one of the `external:` URLs in `_config.yml` to `""` removes it from the menu, home page and footer.

## Publishing on GitHub Pages (Jekyll)

1. Push this folder to a GitHub repository.
2. In the repository go to **Settings → Pages**, choose **Deploy from a branch**, branch `main`, folder `/ (root)`.
3. If the repo is not named `<org>.github.io`, set `baseurl: "/<repo-name>"` in `_config.yml`.

GitHub rebuilds the site on every push, so editing a YAML file in GitHub's web editor is enough to update it.

## Building plain HTML instead

`build.py` renders the same templates and YAML into an `_html/` folder of plain HTML with relative links. You can open that folder from disk or upload it to any web server. It needs `pyyaml`, `jinja2` and `markdown`.

```bash
python build.py
```

In a Jupyter notebook, run `%run build.py` from this folder.
