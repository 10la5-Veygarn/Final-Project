# Inanis

A small Flask-based document editor.

While brainstorming ideas for the CS50P final project, I thought of many different projects, but I ultimately decided to build this simple editor both to convince myself to write something (code and otherwise) and as a simple project which I can build upon. I have some experience with Flask, so I decided to make it web-based first. I might update it to use a more modern front-end framework in the future, but that depends on how lazy I feel.

## Features

- Create, save, rename, and delete plain-text documents
- Automatic, collision-safe naming for new documents (`NewDoc1`, `NewDoc2`, ...) — never overwrites an existing file by accident
- Live word count and estimated reading time
- Documents are stored as plain `.txt` files in `~/Documents/Inanis`, so they're readable without the app if you ever need them

## Structure

- `project.py` — the Flask application, the `Document` model, and three standalone utility functions, all in one file
- `test_project.py` — tests for the three standalone functions, run with `pytest`
- `templates/` — HTML templates
- `static/` — CSS and JavaScript

`project.py` is one file rather than being split across `app.py` and `document.py` (which is how I originally built it) because CS50P's final project requirements call for `main()` and three or more supporting functions to live in `project.py`, at the top level, not nested inside a class. The `Document` class itself still does the real work of managing a document — reading, writing, naming, validating — but the three functions below are pulled out as plain functions so they're independently testable and satisfy that requirement without duplicating logic in two places:

- `count_words(text)` — counts words in a string, treating hyphenated, apostrophe'd, and dotted words ("well-known", "don't", "U.S.A.") as one word each
- `calculate_reading_time(word_count, words_per_minute=200)` — converts a word count into estimated minutes to read
- `validate_document_name(name)` — checks a document name for empty strings, illegal filesystem characters, and reserved Windows filenames (`CON`, `PRN`, etc.)

`Document`'s own methods (`word_counter()`, `reading_time()`, `rename()`, ...) call these three functions internally rather than re-implementing the same logic, so there's one source of truth whether you're using the class or the plain functions directly.

### The `Document` class

The `Document` class is the document model and handles all filesystem operations. Its main methods are:

- `from_file()` — opens a document from the default directory, reads its properties, and builds a `Document` object from the file's name and content
- `save_document()` — saves the document to the default directory as a new file. Checks for name availability and OS permissions, and validates the name before writing. Refuses to overwrite an existing file, instead appending `(1)`, `(2)`, etc. Encoding is UTF-8 (not currently configurable)
- `overwrite()` — saves in place, replacing the existing file under the document's current name. This is what a plain "Save" action uses after the first save
- `delete_document()` — looks up the file path from the document's name and deletes it, raising if the file doesn't exist
- `rename()` — validates a new name, moves the underlying file if one exists on disk, and updates the object's own `name` to match
- `list_documents()` — lists all supported documents in the default directory
- `word_counter()`, `reading_time()`, `exists()`, and a few other smaller helpers

`project.py` needs nothing beyond Flask and the standard library — `pathlib`, `re`, `datetime`, and `typing` are the only other imports. It does need OS-level permissions to create its storage directory and read/write files there. Error handling is exception-based throughout: filesystem and validation errors are raised from `Document`'s methods and caught in the Flask routes, where they're shown to the user as a flash message before falling back to a safe redirect.

### Flask routes

The Flask routes serve the web interface and call straight into `Document` for anything that touches a file. The main routes are:

- `new_document()` — creates a `Document` in memory and redirects to `/edit/<filename>?is_new=1`. Nothing is written to disk until the first save, so closing the tab before saving a brand-new document loses it
- `edit()` — serves the edit page. For a new, unsaved document it builds the `Document` in memory; otherwise it loads the file from disk and computes `reading_time()` for display
- `save()` — a POST route. Calls `save_document()` for a new document or `overwrite()` for an existing one, depending on which the request is for
- `delete()` — a POST route that deletes a document from the filesystem
- `rename()` — a POST route that renames a document on disk

Most error handling lives here, since the routes catch whatever `Document` raises and turn it into a flash message the user actually sees. Every route redirects afterward — either to the home page or back to the document's edit page. There's a Flask secret key set for session/flash support, which is fine for local, single-user use but isn't meant to be secure; this app isn't intended to be exposed on a network.

The `templates/` and `static/` directories hold the HTML, CSS, and JavaScript. They're kept deliberately simple, since the interesting part of this project for a Python course is `project.py`, not the front end.

## Prerequisites

- Python 3
- Flask
- Git
- A terminal or command prompt
- `pytest`, if you want to run the tests (optional)

## To run this

### Linux / macOS

```bash
git clone https://github.com/10la5-Veygarn/inanis.git
cd inanis
python3 -m pip install -r requirements.txt
python3 project.py
```

### Windows

```powershell
git clone https://github.com/10la5-Veygarn/inanis.git
cd inanis
python -m pip install -r requirements.txt
python project.py
```

Then open `http://127.0.0.1:5000` in your browser.

## Running the tests

```bash
python3 -m pip install pytest
pytest test_project.py
```
