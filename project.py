import datetime
import pathlib
import re

from flask import Flask, flash, redirect, render_template, request, url_for

path = pathlib.Path.home() / "Documents" / "Veyalitor"


try:
    path.mkdir(parents=True, exist_ok=True)
except (PermissionError, OSError) as e:
    raise RuntimeError(f"Could not create document directory: {e}") from e


# ---------------------------------------------------------------------------
# Top-level functions.
#
# These hold the pure logic that doesn't need any Document state (no file
# I/O, no `self`) and are what test_project.py tests directly. Document's
# own methods below call these rather than duplicating the logic, so there
# is one source of truth either way you use it: as a plain function, or
# through the class.
# ---------------------------------------------------------------------------

def count_words(text):
    """Count the words in `text`. Hyphenated, apostrophe'd, and dotted
    words ("well-known", "don't", "U.S.A.") each count as a single word."""

    if not isinstance(text, str):
        raise TypeError("text must be a string.")

    return len(re.findall(r"\b\w+(?:['\-.]\w+)*\b", text))


def calculate_reading_time(word_count, words_per_minute=200):
    """Return estimated reading time, in minutes, for a given word count."""

    if not isinstance(word_count, int) or isinstance(word_count, bool):
        raise TypeError("word_count must be an int.")

    if word_count < 0:
        raise ValueError("word_count cannot be negative.")

    if not isinstance(words_per_minute, (int, float)) or isinstance(words_per_minute, bool):
        raise TypeError("words_per_minute must be a number.")

    if words_per_minute <= 0:
        raise ValueError("words_per_minute must be greater than zero.")

    return word_count / words_per_minute


def validate_document_name(name):
    """Raise if `name` isn't a safe, usable document name; otherwise
    return it unchanged."""

    if not isinstance(name, str):
        raise TypeError("Document name must be a string.")

    if not name.strip():
        raise ValueError("Document name cannot be empty.")

    if name in {".", ".."}:
        raise ValueError("Invalid document name.")

    if any(char in name for char in '<>:"/\\|?*'):
        raise ValueError("Document name contains invalid characters.")

    # Windows reserved filenames
    if name.upper().split(".")[0] in {
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5",
        "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5",
        "LPT6", "LPT7", "LPT8", "LPT9"
    }:
        raise ValueError("This is a reserved filename.")

    return name


# ---------------------------------------------------------------------------
# Document class — same design as before, now delegating to the functions
# above instead of holding its own copies of that logic.
# ---------------------------------------------------------------------------

class Document:

    _default_location = path
    _known_extensions = {"txt"}  # extend this set as new formats are added

    def __init__(self):
        largest_n = self._next_doc_number()

        n = largest_n + 1

        self.name = f"NewDoc{n}"
        self.content = ""
        self.word_count = 0
        self._init_time = datetime.datetime.now()
        self.ext = "txt"

    @classmethod
    def _next_doc_number(cls):
        try:
            numbers = (
                int(match.group(1))
                for file in cls._default_location.iterdir()
                if file.is_file()
                if (match := re.search(r"^NewDoc(\d+)", file.stem))
            )

            return max(numbers, default=0)

        except PermissionError as e:
            raise PermissionError(
                f"Could not inspect document directory: {e}"
            ) from e
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"Could not inspect document directory: {e}"
            ) from e
        except OSError as e:
            raise OSError(f"Could not inspect document directory: {e}") from e

    def word_counter(self):
        self.word_count = count_words(self.content)
        return self.word_count

    def _get_available_path(self, location):
        location = pathlib.Path(location)

        file = location / f"{self.name}.{self.ext}"

        if not file.exists():
            return file

        n = 1

        while True:
            file = location / f"{self.name}({n}).{self.ext}"

            if not file.exists():
                return file

            n += 1

    def _validated_target_path(self, path):
        if path is None:
            path = self._default_location

        path = pathlib.Path(path)

        validate_document_name(self.name)

        if not isinstance(self.ext, str):
            raise TypeError("Document extension must be a string.")

        if not self.ext or any(char in self.ext for char in '/\\'):
            raise ValueError("Invalid document extension.")

        if not path.exists():
            raise FileNotFoundError(
                f"Document directory does not exist: {path}"
            )

        if not path.is_dir():
            raise NotADirectoryError(
                f"Document location is not a directory: {path}"
            )

        return path

    def save_document(self, path=None):
        """Save as a new file. Refuses to overwrite an existing file,
        instead appending (1), (2), etc. Use this for 'Save As' style
        behaviour, or for the very first save of a new document."""

        path = self._validated_target_path(path)
        file = self._get_available_path(path)

        try:
            with open(file, "x", encoding="utf-8") as f:
                f.write(self.content)

        except PermissionError as e:
            raise PermissionError(f"Could not save document: {e}") from e
        except OSError as e:
            raise OSError(f"Could not save document: {e}") from e

        return file

    def overwrite(self, path=None):
        """Save in place, replacing the existing file under this
        document's current name if one exists. This is what a plain
        'Save' action in the editor should call."""

        path = self._validated_target_path(path)
        file = path / f"{self.name}.{self.ext}"

        try:
            with open(file, "w", encoding="utf-8") as f:
                f.write(self.content)

        except PermissionError as e:
            raise PermissionError(f"Could not save document: {e}") from e
        except OSError as e:
            raise OSError(f"Could not save document: {e}") from e

        return file

    def rename(self, name, path=None):
        validate_document_name(name)

        if path is None:
            path = self._default_location

        path = pathlib.Path(path)
        old_file = path / f"{self.name}.{self.ext}"

        if old_file.exists():
            new_file = path / f"{name}.{self.ext}"

            if new_file.exists():
                raise FileExistsError(
                    f"A document named {new_file.name!r} already exists."
                )

            try:
                old_file.rename(new_file)
            except PermissionError as e:
                raise PermissionError(f"Could not rename document: {e}") from e
            except OSError as e:
                raise OSError(f"Could not rename document: {e}") from e

        self.name = name

    def delete_document(self, path=None):
        if path is None:
            path = self._default_location

        path = pathlib.Path(path)

        file = path / f"{self.name}.{self.ext}"

        if not file.exists():
            raise FileNotFoundError(
                f"Document does not exist: {file}"
            )

        try:
            file.unlink()
        except PermissionError as e:
            raise PermissionError(f"Could not delete document: {e}") from e
        except OSError as e:
            raise OSError(f"Could not delete document: {e}") from e

    def exists(self, path=None):
        if path is None:
            path = self._default_location

        path = pathlib.Path(path)

        file = path / f"{self.name}.{self.ext}"

        return file.is_file()

    def reading_time(self, words_per_minute=200):
        self.word_counter()
        return calculate_reading_time(self.word_count, words_per_minute)

    def to_dict(self):
        return {
            "name": self.name,
            "content": self.content,
            "word_count": self.word_count,
            "extension": self.ext,
            "init_time": self._init_time.isoformat()
        }

    @classmethod
    def from_file(cls, filename, path=None):
        if path is None:
            path = cls._default_location

        path = pathlib.Path(path)
        file_path = path / filename

        if not file_path.is_file():
            raise FileNotFoundError(
                f"Document does not exist: {file_path}"
            )

        name = file_path.stem
        ext = file_path.suffix.removeprefix(".")

        # Validate before reading, so a bad filename fails fast with a
        # clear error rather than loading content into a Document that
        # can't later be saved or renamed under its own loaded name.
        validate_document_name(name)

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()

        except PermissionError as e:
            raise PermissionError(
                f"Permission denied when reading {file_path}"
            ) from e

        except UnicodeDecodeError as e:
            raise UnicodeDecodeError(
                e.encoding,
                e.object,
                e.start,
                e.end,
                f"Could not decode document {file_path}: {e.reason}"
            ) from e

        except OSError as e:
            raise OSError(f"Could not read document: {e}") from e

        newdoc = cls()

        newdoc.content = content
        newdoc.name = name
        newdoc.ext = ext
        newdoc.word_count = newdoc.word_counter()

        return newdoc

    @classmethod
    def list_documents(cls, path=None):
        if path is None:
            path = cls._default_location

        path = pathlib.Path(path)

        try:
            return sorted(
                file.name
                for file in path.iterdir()
                if file.is_file()
                if file.suffix.removeprefix(".") in cls._known_extensions
            )

        except PermissionError as e:
            raise PermissionError(f"Could not list documents: {e}") from e
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Could not list documents: {e}") from e
        except OSError as e:
            raise OSError(f"Could not list documents: {e}") from e

    def __repr__(self):
        return (
            f"Document(name={self.name!r}, "
            f"extension={self.ext!r}, "
            f"word_count={self.word_count})"
        )


# ---------------------------------------------------------------------------
# Flask app (previously app.py) — routes are unchanged, just living
# alongside Document in the same file now.
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.secret_key = "dev"  # fine for local single-user use; not for production


@app.route("/")
def index():
    try:
        documents = Document.list_documents()
    except (PermissionError, FileNotFoundError, OSError) as e:
        flash(str(e))
        documents = []

    return render_template("index.html", documents=documents)


@app.route("/new")
def new_document():
    doc = Document()
    return redirect(url_for("edit", filename=f"{doc.name}.{doc.ext}", is_new="1"))


@app.route("/edit/<filename>")
def edit(filename):
    is_new = request.args.get("is_new") == "1"

    if is_new:
        # A brand-new document that hasn't been saved to disk yet.
        # Reconstruct it in memory rather than requiring a file to exist.
        name, _, ext = filename.rpartition(".")
        doc = Document()
        doc.name = name
        doc.ext = ext
        return render_template("editor.html", doc=doc, is_new=True,
                                reading_time=0.0)

    try:
        doc = Document.from_file(filename)
    except FileNotFoundError:
        flash(f"No such document: {filename}")
        return redirect(url_for("index"))
    except (PermissionError, UnicodeDecodeError, OSError) as e:
        flash(str(e))
        return redirect(url_for("index"))

    return render_template("editor.html", doc=doc, is_new=False,
                            reading_time=doc.reading_time())


@app.route("/save/<filename>", methods=["POST"])
def save(filename):
    content = request.form.get("content", "")
    is_new = request.form.get("is_new") == "1"

    name, _, ext = filename.rpartition(".")
    doc = Document()
    doc.name = name
    doc.ext = ext
    doc.content = content
    doc.word_counter()

    try:
        if is_new:
            saved_path = doc.save_document()
        else:
            saved_path = doc.overwrite()
    except (PermissionError, OSError, FileNotFoundError, ValueError,
            TypeError, NotADirectoryError) as e:
        flash(f"Could not save: {e}")
        return redirect(url_for("edit", filename=filename,
                                 is_new="1" if is_new else None))

    flash("Saved.")
    return redirect(url_for("edit", filename=saved_path.name))


@app.route("/delete/<filename>", methods=["POST"])
def delete(filename):
    name, _, ext = filename.rpartition(".")
    doc = Document()
    doc.name = name
    doc.ext = ext

    try:
        doc.delete_document()
        flash(f"Deleted {filename}.")
    except FileNotFoundError:
        flash(f"No such document: {filename}")
    except (PermissionError, OSError) as e:
        flash(str(e))

    return redirect(url_for("index"))


@app.route("/rename/<filename>", methods=["POST"])
def rename(filename):
    new_name = request.form.get("new_name", "")

    name, _, ext = filename.rpartition(".")
    doc = Document()
    doc.name = name
    doc.ext = ext

    try:
        doc.rename(new_name)
        flash("Renamed.")
    except (ValueError, TypeError):
        flash("That name isn't valid.")
        return redirect(url_for("edit", filename=filename))
    except FileExistsError as e:
        flash(str(e))
        return redirect(url_for("edit", filename=filename))
    except (PermissionError, OSError) as e:
        flash(str(e))
        return redirect(url_for("edit", filename=filename))

    return redirect(url_for("edit", filename=f"{doc.name}.{doc.ext}"))


# ---------------------------------------------------------------------------
# main() — the required entry point. Running `python project.py` starts
# the Flask development server.
# ---------------------------------------------------------------------------

def main():
    app.run(debug=True)


if __name__ == "__main__":
    main()
