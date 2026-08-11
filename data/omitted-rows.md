# The 50 rows omitted from the published files

These extensions exist and were collected. Each one is omitted for the same reason: its
**publisher id has the shape of a secret**, and a dataset that ships it is a credential
dump whether or not the string is live. They are listed here in full so that nothing is
hidden by being removed, and `scripts/crawl.py` regenerates the complete set including
them — run `scripts/scrub.py` afterwards to reproduce exactly the files published here.

Combined installs across all 50: 208,593. 50 of 64,514 collected rows is
0.08% of the crawl, and it moves no headline figure in the README.

## 26 rows: publisher id is a bare UUID

GitHub's secret scanning matches a bare UUID as an **Open VSX access token**, and it is also
the shape this field takes when a publish token reaches the slot a namespace should occupy.
They were **not tested against Open VSX** — that would mean using somebody else's credential,
and the decision to omit them does not depend on the answer.

| Extension | Category | Installs |
|---|---|---:|
| python-silver-pack | Linters | 60,229 |
| vscode-nier-automata-theme | Themes | 16,359 |
| front-end-extension-gold-pack | Extension Packs | 10,017 |
| vscode-pets-advanced | Visualization | 6,063 |
| gloom-dark | Themes | 5,333 |
| tagclassname | Snippets | 2,878 |
| md-office-editor | Formatters | 1,353 |
| software-translation-tool | Other | 853 |
| csspro-sorter | Formatters | 567 |
| preact-snippets | Snippets | 488 |
| vscode-dependency-visualizer | Debuggers | 475 |
| nvidia-agent | AI | 396 |
| codepolish | Formatters | 232 |
| orange-in-black-by-jalal | Themes | 222 |
| quantum-blue-theme | Themes | 169 |
| cpp-snippets-pst | Snippets | 121 |
| kenkei-snippets | Snippets | 104 |
| jinie-tm-mediazen | Extension Packs | 82 |
| jinie-lsp-mediazen | Extension Packs | 49 |
| jonasjsdoc | Extension Packs | 37 |
| 01protocol | AI | 24 |
| SectionKit | Snippets | 13 |
| PitcherPro | Formatters | 13 |
| yaarscript | Education | 9 |
| axon-api-client | Testing | 8 |
| yaarscript-snippets | Education | 2 |

## 24 rows: publisher id is a 52-character base32 string

GitHub's secret scanning misclassifies this as an Azure DevOps personal access token, which
blocks any push containing them. These are public identifiers, not credentials — the
unauthenticated Marketplace API returns them on request.

| Extension | Category | Installs |
|---|---|---:|
| copyplaintext | Formatters | 47,126 |
| python-visual-cli | Programming Languages | 11,197 |
| darkplus-php-plum-tags | Themes | 9,777 |
| eslint-plugin-linting-lightning | Other | 7,336 |
| TTK | Other | 4,272 |
| lightplus-php-purple-tags | Themes | 3,812 |
| django-kick-start | Programming Languages | 3,659 |
| flutter-fly | Snippets | 2,989 |
| diana-coding | Other | 2,766 |
| lc3-lang | Programming Languages | 2,676 |
| MistyBlue | Themes | 2,393 |
| color-blind-dark | Themes | 1,205 |
| ahtml-django-snippets | Snippets | 887 |
| color-blind-light | Themes | 724 |
| hedy | Programming Languages | 440 |
| engineer-theme | Themes | 437 |
| dark-theme-pro | Themes | 247 |
| flutter-snippets-helper | Snippets | 148 |
| zmextension | Snippets | 121 |
| chen-vue-snippets | Snippets | 106 |
| conan51551-snipper | Snippets | 65 |
| GMX | Snippets | 52 |
| retech-template | Extension Packs | 49 |
| retech-Snippets | Snippets | 13 |
