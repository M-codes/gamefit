# GameFit 🎮

**A personal gaming analytics project built with Python, PostgreSQL and Power BI.**

GameFit combines my own game ratings and playing habits with Steam library data and RAWG metadata. It explores where I spend my gaming time, which games I enjoy, why I stop playing, and which unfinished games I might revisit.

The current dataset contains **30 manually labelled games**, matched against an extract of **113 Steam library records**. This is a personal learning project and a small, selected sample—not a study of all players or my entire library.

## Questions the project explores

- Which games account for most of my recorded playtime?
- Do the games I play most also receive my highest ratings?
- Which games have I completed, paused or abandoned?
- What reasons have I recorded for stopping?
- Which highly rated games could I return to, given how I want to play?

## Current features

- Python processing of manually labelled game data.
- Steam library extraction and matching to the selected games.
- RAWG metadata enrichment with a manual match-review step.
- Processed CSV and Parquet datasets.
- PostgreSQL staging, dimension and fact tables.
- A Power BI analysis view verified to contain **30 rows and 30 distinct library keys**.
- Interactive status and playtime charts.
- A scatter chart comparing playtime with personal rating.
- A game details table for exploring individual games and stopping reasons.
- A **Play Next** shortlist based on playing/paused status and personal rating.

An adjustable minimum-rating parameter has been specified for the shortlist; Verified that changing the minimum rating from 9 to 6 updates the shortlist correctly. The shortlist uses explicit rules, not a trained machine-learning model.

## Report pages

| Page | Purpose |
|---|---|
| Overview | Explore game status and playtime, with a status slicer. |
| Enjoyment vs Time | Compare hours played with personal ratings; select a game to inspect its details. |
| Play Next | Shortlist playing or paused games with high personal ratings, with a play-context filter. |

The initial shortlist cutoff is **8/10**. The planned adjustable control allows the user to change that cutoff without changing the saved ratings.

## Dashboard screenshots

### Overview
Game status and playtime, with interactive filtering.

![GameFit overview](docs/screenshots/Overview.png)

### Enjoyment vs Time
Personal ratings compared with recorded playtime.
Selecting a game reveals its details and stopping reason.

![Enjoyment versus playtime](docs/screenshots/EnjoymentvsTime.png)

### Play Next
A shortlist of playing or paused games, filtered by
an adjustable minimum personal rating and play context.

![Play Next shortlist](docs/screenshots/PlayNext.png)

## Data sources

| Source | Contribution |
|---|---|
| Manual CSV | Personal rating, status, recommendation, stopping reason, play context, and known purchase details. |
| Steam Web API | Steam app identifiers, recorded playtime and available last-played information. |
| RAWG API | Matched catalogue identifiers and available game metadata, including release information, genres and ratings. |

Manual labels describe my own experience. External metadata supplements those labels. Unknown purchase prices, dates and ratings remain missing rather than being invented or replaced with zero.

Steam playtime is converted from minutes to **hours** for analysis. A game’s recorded playtime does not necessarily represent focused or enjoyable play: it can include idle time and repeat sessions.

## Data flow

1. Record personal labels in `data/manual/library.csv`.
2. Extract Steam and RAWG responses and retain raw JSON locally.
3. Match game records and review ambiguous catalogue matches.
4. Combine subjective labels and external data into processed CSV/Parquet files.
5. Load the master dataset into `analytics.stg_library` in PostgreSQL.
6. Merge staged records into game, platform, storefront, genre and library tables.
7. Query `analytics.vw_library_analysis` from Power BI using Import mode.

Changing a source CSV alone does not update Power BI. The affected processing and database-loading steps must be rerun, followed by a Power BI refresh.

## Technology

| Tool | Role |
|---|---|
| Python 3.13 | Extraction, matching, transformation and loading. |
| pandas | Tabular data processing. |
| PyArrow | Parquet support. |
| requests | API requests. |
| SQLAlchemy and psycopg | PostgreSQL connections and loading. |
| python-dotenv | Local environment configuration. |
| PostgreSQL / pgAdmin 4 | Database storage, SQL execution and inspection. |
| Power BI Desktop / DAX | Interactive reporting and shortlist calculations. |
| pytest | Automated checks of transformation behaviour. |
| Git / VS Code | Version control and development. |

## Project layout

The main project locations are:

| Location | Contents |
|---|---|
| `src/gamefit/extract/` | API extraction modules. |
| `src/gamefit/transform/` | Validation, matching and source-merging logic. |
| `src/gamefit/load/` | PostgreSQL loading modules. |
| `src/gamefit/config.py` | Project paths and environment settings. |
| `src/gamefit/pipeline.py` | Manual-data processing pipeline. |
| `data/manual/` | Manually maintained input data. |
| `data/raw/` | Saved source responses. |
| `data/processed/` | Processed and enriched outputs. |
| `sql/` | Schema, merge, view and quality-check scripts. |
| `tests/` | Automated tests. |
| `docs/` | Data definitions and project notes. |
| `powerbi/` | Power BI report files. |

## Local setup

The project was developed on Windows using PowerShell, a Python virtual environment, and a local PostgreSQL 17 server.

From the project root, create and activate a virtual environment if one does not already exist:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the dependencies and the local package:

```powershell
python -m pip install -r requirements.txt
python -m pip install -e .
```

Create a local `.env` file in the project root, using `.env.example` as a template if available:

```dotenv
DATABASE_URL=postgresql+psycopg://gamefit:YOUR_URL_ENCODED_PASSWORD@localhost:5432/gamefit
STEAM_API_KEY=YOUR_STEAM_API_KEY
STEAM_ID64=YOUR_STEAM_ID64
RAWG_API_KEY=YOUR_RAWG_API_KEY
```

Use the PostgreSQL role and connection details configured on your machine. URL-encode special characters in the password when placing it in a connection URL.

Keep real credentials in `.env`, exclude that file from Git, and put only placeholders in `.env.example`. Review raw data and report contents before publishing them.

### Processing and database setup

The development workflow currently includes manual SQL execution in pgAdmin. It is not yet a verified one-command installation.

- Create the `gamefit` database and application role.
- Apply the schema SQL and confirm the role has the permissions needed for loading.
- Add the manual input CSV and configure API access.
- Run extraction, matching and enrichment before loading the master dataset.
- Run the appropriate merge SQL, then create or update the analysis view.

The manual pipeline command used during development is:

```powershell
python -m gamefit.pipeline
```

This pipeline has been used to validate the manual CSV, write Parquet and load staging. **Do not assume it runs the complete Steam/RAWG enrichment workflow.** Loading manual-only data can replace an enriched staging table; use the master-data loader when preparing the enriched merge.

The final database scripts used during development include `005_merge_master.sql` and `006_views_master.sql`. Run scripts against the intended database and inspect errors before continuing. The library model includes a storefront key; merges must respect the actual table constraints.

### Power BI connection

Open Power BI Desktop and connect to PostgreSQL using your local settings:

| Setting | Development value |
|---|---|
| Server | `localhost:5432` |
| Database | `gamefit` |
| Connectivity mode | Import |
| View | `analytics.vw_library_analysis` |

The imported table is named **Game Library** in the report. DAX expressions reference that name. Save the report as `powerbi/GameFit.pbix`.

## Validation and testing

Validation checks the actual input data against implemented rules. Automated tests check whether the code behaves as expected using controlled examples. Passing one test does not establish that every real-world data issue has been checked.

Checks used during development include required columns, allowed status values, unique game identifiers, personal-rating bounds, staging row counts and RAWG ID presence. Some conversion logic can turn invalid numeric or date strings into missing values, so missingness also needs review.

Run the existing automated tests from the project root:

```powershell
python -m pytest -q
```

Check the final analysis view in pgAdmin:

```sql
SELECT
    COUNT(*) AS total_rows,
    COUNT(DISTINCT library_key) AS unique_library_rows
FROM analytics.vw_library_analysis;
```

For the current selected dataset, the expected result is **30 / 30**. This checks row count and key uniqueness; it does not by itself verify every field or catalogue match. Update this expectation deliberately when expanding the dataset.

## Initial observations

In the dashboard snapshot reviewed on **19 September 2026**, **15 of the 30 labelled games were paused (50%)**. This describes the selected sample at that time, not the entire 113-game Steam extract.

The scatter chart showed high personal ratings at both low and high playtimes. This is an exploratory observation; no statistical relationship or causal claim has been established.

## Limitations

- The dataset represents one person and 30 selected games.
- Purchase details and some external metadata may be missing.
- Multiplayer and ongoing games may have no meaningful completion endpoint.
- Catalogue matches require care around editions, remakes and similarly named titles.
- RAWG playtime metadata is not a reliable estimate of remaining story time.
- The shortlist favours games already rated; it does not predict enjoyment of unrated games.
- A `solo`, `multi` or `both` label records play context. Exact slicer selections treat these as separate categories.
- API access, permissions and source data can affect reproducibility.

## Next milestones

- [X] Verify the minimum-rating parameter at 9 and 6, including exclusion of unrated games.
- [ ] Confirm the fixed rating filter is removed when enabling the adjustable cutoff.
- [ ] Add report screenshots and a short explanation of each page.
- [ ] Document the exact extraction-to-refresh command sequence from the current code.
- [ ] Review missing values and add tests for additional validation edge cases.
- [ ] Record further findings with sample sizes and limitations.

## Attribution

Game metadata is provided by [RAWG](https://rawg.io/). Steam library data comes from the [Steam Web API](https://steamcommunity.com/dev). Personal ratings and labels are my own.

This is an independent learning project and is not affiliated with Valve or RAWG. Follow the applicable provider terms when using or displaying their data.
