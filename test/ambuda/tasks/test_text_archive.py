"""Unit tests for create_text_archive_inner.

All DB, S3, and XML-generation calls are mocked so these tests
never touch the filesystem or network.
"""

import json
import zipfile
from unittest.mock import MagicMock, patch

import pytest

import ambuda.database as db
from ambuda.tasks.text_exports import create_text_archive_inner


def _make_text(
    id=1,
    slug="test-text",
    title="Test Text",
    header="<teiHeader/>",
    config=None,
    language="sa",
    status="published",
    genre_name=None,
    collection_slugs=None,
):
    text = MagicMock()
    text.id = id
    text.slug = slug
    text.title = title
    text.header = header
    text.config = json.dumps(config) if config else None
    text.language = language
    text.status = status

    if genre_name:
        text.genre.name = genre_name
    else:
        text.genre = None

    text.collections = []
    for cs in collection_slugs or []:
        c = MagicMock()
        c.slug = cs
        text.collections.append(c)

    return text


def _make_text_export(s3_path="s3://bucket/assets/text-exports/test-text.xml"):
    export = MagicMock()
    export.export_type = "xml"
    export.s3_path = s3_path
    return export


class Mocks:
    """Container for the four mocks used by every test."""

    def __init__(self, get_db_session, create_xml_file, task_s3, utils_s3):
        self.get_db_session = get_db_session
        self.create_xml_file = create_xml_file
        self.task_s3 = task_s3
        self.utils_s3 = utils_s3

    def setup_session(self, texts, exports_by_text_id=None, bulk_export=None):
        """Wire the DB session mock to return the given texts and exports."""
        session = MagicMock()
        self.session = session
        self.added = []
        session.add.side_effect = self.added.append
        exports = exports_by_text_id or {}
        self._bulk_export = bulk_export

        def fake_query(model):
            q = MagicMock()

            if model is db.Text:
                q.all.return_value = texts

            def fake_filter(*args, **kwargs):
                fq = MagicMock()
                if model is db.TextExport:
                    for text_id, export in exports.items():
                        fq.first.return_value = export
                        return fq
                    fq.first.return_value = None
                elif model is db.BulkExport:
                    fq.first.return_value = self._bulk_export
                return fq

            q.filter.return_value = q
            q.filter.side_effect = fake_filter
            return q

        session.query.side_effect = fake_query

        config = MagicMock()
        config.S3_BUCKET = "test-bucket"

        self.get_db_session.return_value.__enter__ = MagicMock(
            return_value=(session, MagicMock(), config)
        )
        self.get_db_session.return_value.__exit__ = MagicMock(return_value=False)
        return config

    def capture_upload(self):
        """Set up S3 mock to capture the uploaded ZIP contents. Returns the dict."""
        uploaded = {}

        def _capture(path):
            with zipfile.ZipFile(path, "r") as zf:
                uploaded["names"] = sorted(zf.namelist())
                uploaded["metadata"] = json.loads(zf.read("metadata.json"))

        mock_s3_instance = MagicMock()
        mock_s3_instance.upload_file.side_effect = _capture
        self.utils_s3.return_value = mock_s3_instance
        return uploaded

    def fake_create_xml(self, content="<TEI/>"):
        """Set up create_xml_file to write a dummy file."""

        def _create(t, path):
            path.write_text(content)

        self.create_xml_file.side_effect = _create


@pytest.fixture
def export_mocks():
    with (
        patch("ambuda.tasks.text_exports.get_db_session") as mock_get_db,
        patch("ambuda.tasks.text_exports.create_xml_file") as mock_create_xml,
        patch("ambuda.tasks.text_exports.S3Path") as mock_task_s3,
        patch("ambuda.utils.text_exports.S3Path") as mock_utils_s3,
    ):
        yield Mocks(mock_get_db, mock_create_xml, mock_task_s3, mock_utils_s3)


def test_metadata_fields(export_mocks):
    """metadata.json contains correct fields for each text."""
    text = _make_text(
        id=1,
        slug="gita",
        title="Bhagavad Gita",
        header="<teiHeader/>",
        config={"headings": "chapter"},
        language="sa",
        status="published",
        genre_name="kavya",
        collection_slugs=["itihasa", "classics"],
    )
    export_mocks.setup_session([text])
    uploaded = export_mocks.capture_upload()

    create_text_archive_inner("testing")

    assert len(uploaded["metadata"]) == 1
    m = uploaded["metadata"][0]
    assert m["slug"] == "gita"
    assert m["title"] == "Bhagavad Gita"
    assert m["header"] == "<teiHeader/>"
    assert m["config"] == {"headings": "chapter"}
    assert m["language"] == "sa"
    assert m["status"] == "published"
    assert m["genre"] == "kavya"
    assert m["collections"] == ["itihasa", "classics"]


def test_downloads_from_s3_when_export_exists(export_mocks):
    """When a TextExport with s3_path exists, downloads XML from S3."""
    text = _make_text(id=1, slug="gita")
    export = _make_text_export("s3://bucket/assets/text-exports/gita.xml")
    export_mocks.setup_session([text], {1: export})

    mock_s3_from_path = MagicMock()
    export_mocks.task_s3.from_path.return_value = mock_s3_from_path

    def fake_download(path):
        path.write_text("<TEI/>")

    mock_s3_from_path.download_file.side_effect = fake_download
    export_mocks.task_s3.return_value = MagicMock()

    create_text_archive_inner("testing")

    export_mocks.task_s3.from_path.assert_called_once_with(
        "s3://bucket/assets/text-exports/gita.xml"
    )
    mock_s3_from_path.download_file.assert_called_once()
    export_mocks.create_xml_file.assert_not_called()


def test_falls_back_to_generate_when_no_export(export_mocks):
    """When no TextExport exists, falls back to create_xml_file."""
    text = _make_text(id=1, slug="gita")
    export_mocks.setup_session([text], {})
    export_mocks.fake_create_xml()
    export_mocks.task_s3.return_value = MagicMock()

    create_text_archive_inner("testing")

    export_mocks.create_xml_file.assert_called_once()
    assert export_mocks.create_xml_file.call_args[0][0] is text


def test_falls_back_on_s3_download_failure(export_mocks):
    """When S3 download fails, falls back to create_xml_file."""
    text = _make_text(id=1, slug="gita")
    export = _make_text_export("s3://bucket/assets/text-exports/gita.xml")
    export_mocks.setup_session([text], {1: export})

    mock_s3_from_path = MagicMock()
    mock_s3_from_path.download_file.side_effect = Exception("S3 is down")
    export_mocks.task_s3.from_path.return_value = mock_s3_from_path

    export_mocks.fake_create_xml()
    export_mocks.task_s3.return_value = MagicMock()

    create_text_archive_inner("testing")

    export_mocks.create_xml_file.assert_called_once()


def test_no_texts_skips_upload(export_mocks):
    """When there are no texts in the DB, no ZIP is created or uploaded."""
    export_mocks.setup_session([])

    create_text_archive_inner("testing")

    export_mocks.create_xml_file.assert_not_called()
    export_mocks.task_s3.assert_not_called()


def test_upload_destination(export_mocks):
    """ZIP is uploaded to the correct S3 bucket and key."""
    text = _make_text(id=1, slug="gita")
    cfg = export_mocks.setup_session([text])
    cfg.S3_BUCKET = "my-bucket"
    export_mocks.fake_create_xml()

    mock_s3_instance = MagicMock()
    export_mocks.utils_s3.return_value = mock_s3_instance

    create_text_archive_inner("testing")

    call_args = export_mocks.utils_s3.call_args
    assert call_args[0][0] == "my-bucket"
    assert call_args[0][1] == "assets/text-exports/ambuda-xml.zip"
    mock_s3_instance.upload_file.assert_called_once()


def test_zip_contains_xml_and_metadata(export_mocks):
    """The uploaded ZIP contains XML files and metadata.json."""
    texts = [
        _make_text(id=1, slug="gita", title="Gita"),
        _make_text(id=2, slug="ramayana", title="Ramayana"),
    ]
    export_mocks.setup_session(texts)
    export_mocks.fake_create_xml()
    uploaded = export_mocks.capture_upload()

    create_text_archive_inner("testing")

    assert uploaded["names"] == ["gita.xml", "metadata.json", "ramayana.xml"]
    assert len(uploaded["metadata"]) == 2
    slugs = [m["slug"] for m in uploaded["metadata"]]
    assert "gita" in slugs
    assert "ramayana" in slugs


def test_null_config_in_metadata(export_mocks):
    """Text with config=None produces null in metadata, not a parse error."""
    text = _make_text(id=1, slug="gita", config=None)
    export_mocks.setup_session([text])
    export_mocks.fake_create_xml()
    uploaded = export_mocks.capture_upload()

    create_text_archive_inner("testing")

    assert uploaded["metadata"][0]["config"] is None


def test_creates_bulk_export_record(export_mocks):
    """Running the archive creates a new BulkExport record."""
    text = _make_text(id=1, slug="gita")
    export_mocks.setup_session([text])
    export_mocks.fake_create_xml()
    export_mocks.capture_upload()

    create_text_archive_inner("testing")

    assert len(export_mocks.added) == 1
    record = export_mocks.added[0]
    assert isinstance(record, db.BulkExport)
    assert record.slug == "ambuda-xml.zip"
    assert record.export_type == "xml"
    assert record.s3_path is not None
    assert record.size > 0
    assert len(record.sha256_checksum) == 64
    export_mocks.session.commit.assert_called_once()


def test_updates_existing_bulk_export_record(export_mocks):
    """Re-running the archive updates the existing BulkExport instead of creating a new one."""
    text = _make_text(id=1, slug="gita")
    existing = MagicMock()
    existing.slug = "ambuda-xml.zip"
    export_mocks.setup_session([text], bulk_export=existing)
    export_mocks.fake_create_xml()
    export_mocks.capture_upload()

    create_text_archive_inner("testing")

    assert len(export_mocks.added) == 0
    assert existing.s3_path is not None
    assert existing.size > 0
    assert len(existing.sha256_checksum) == 64
    assert existing.updated_at is not None
    export_mocks.session.commit.assert_called_once()
