# AI assistance record

This project was generated and refined with Codex in the accompanying conversation.

## Actual user direction

The user supplied Program 30's major-project specification, including an approved theme, Tkinter/PyQt GUI, at least four screens, menu bar, three database tables, CRUD, validation, reports, export/import, an executable and GitHub source. The user accepted the Personal Expense Manager proposal, named Pocket Atlas, and requested strict compliance and an easy-to-find D: folder.

## AI-assisted implementation and debugging

- Implemented four related SQLite tables with validated Python connectivity.
- Used PyQt6 specifically because the question explicitly names Tkinter/PyQt; did not treat PySide6 as an exact substitute for this major project.
- Built six connected screens, a menu bar, a filtered report table and database-driven summaries.
- Stored amounts as integer paise and tested opening balances, income, expenses and monthly budget totals.
- Added JSON export/import with stable record identifiers, relationship mapping, duplicate skipping and all-or-nothing validation.
- Added CSV report export and delete confirmations.
- Tested real Qt widgets without taking screenshots; adjusted the overview heading to wrap at smaller window sizes.
- Built a Windows distributable with PyInstaller. The packaged app uses Local AppData for its SQLite database.

## Student review

The student should inspect and personalise the program, review the generated code, and take genuine screenshots of each screen. This record does not claim the student independently wrote the generated code or has already captured screenshots.
