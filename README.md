# Pocket Atlas — Personal Expense Manager

Program 30, Major Project II. Approved theme: Personal Expense Manager.

Python, **PyQt6**, and SQLite. Six screens: Overview, Transactions, Accounts, Categories, Budgets and Reports. Includes a File / Go to / Help menu bar.

## Run

Double-click `Launch.cmd`. After building, this starts `dist/PocketAtlas/PocketAtlas.exe`. The complete `dist/PocketAtlas` folder is the distributable; copy the whole folder to another Windows computer. Python is not required for the executable.

Source mode uses the sibling `.runtime` Python environment. Install `requirements.txt` into a Python virtual environment when running source elsewhere. `Build.cmd` creates the executable with PyInstaller.

## What is implemented

- Four related SQLite tables: accounts, categories, transactions, budgets.
- Complete CRUD, input validation and confirmation before delete.
- Integer-paise money storage, recalculated balances, monthly totals and category budgets.
- Search and filtered report table by dates, account and income/expense type.
- JSON export **and import back into the application**, retaining relationships and skipping existing record identifiers.
- Atomic import: malformed data is rolled back. Existing edits are preserved for repeated identifiers.
- CSV export of the filtered report with formula-prefix protection.
- Data is local; there is no bank connection. Opening balances are not counted as income.

Source mode stores its database in `data/`. The packaged executable stores it in `%LOCALAPPDATA%/PocketAtlas/` so it can run from a non-writable installation folder. JSON export uses the destination you choose.

Tests: `../.runtime/Scripts/python.exe -m unittest -v test_pocket_atlas`.
The sample exported file supplied for submission is explicitly demo data, not the student's private finances.

AI assistance is documented in `AI_ASSISTANCE.md`. Screenshots will be taken by the student.
