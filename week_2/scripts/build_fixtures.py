#!/usr/bin/env python3
"""
Builds the small, deterministic test fixtures from the live JNU snapshots saved
in fixtures/jnu/live_snapshots/ (captured 2026-09-26).

Real markup is kept (same classes, same nesting); we only cut the page down to
the Drupal view block and a handful of rows so the tests stay readable.
Run from week_2/:  python3 scripts/build_fixtures.py
"""

import copy
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
LIVE = ROOT / "fixtures" / "jnu" / "live_snapshots"
NOTICES = ROOT / "fixtures" / "jnu" / "notices"
EVENTS = ROOT / "fixtures" / "jnu" / "events"
PAGINATION = ROOT / "fixtures" / "pagination"

PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>{title}</title></head>
<body><main role="main">
<!-- fixture: {note} -->
{body}
</main></body></html>
"""


def soup_of(name: str) -> BeautifulSoup:
    return BeautifulSoup((LIVE / name).read_text(encoding="utf-8"), "html.parser")


def view_block(soup: BeautifulSoup, selector: str, keep_rows: int | None) -> BeautifulSoup:
    view = copy.copy(soup.select_one(selector))
    if keep_rows is not None:
        rows = [tr for tr in view.select("table tr") if tr.find("td")]
        for tr in rows[keep_rows:]:
            tr.decompose()
    return view


def write(path: Path, title: str, note: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(PAGE.format(title=title, note=note, body=body), encoding="utf-8")
    print("wrote", path.relative_to(ROOT))


def notice_row(n: int, title: str, href: str | None, date: str | None) -> str:
    link = f'<p><a href="{href}">{title}</a></p>' if href else f"<p>{title}</p>"
    date_cell = f"{date}" if date else ""
    return f"""
    <tr>
      <td class="views-field views-field-counter" headers="view-counter-table-column">{n}</td>
      <td class="views-field views-field-title" headers="view-title-table-column">{link}</td>
      <td class="views-field views-field-field-notice-date" headers="view-field-notice-date-table-column">{date_cell}</td>
      <td class="views-field views-field-field-upload-file" headers="view-field-upload-file-table-column"></td>
    </tr>"""


def notices_view(rows: str, pager: str = "") -> str:
    return f"""<div class="view view-notices view-id-notices view-display-id-page_1">
  <div class="view-content">
    <table class="cols-4">
      <thead><tr>
        <th class="views-field views-field-counter" scope="col">Sl. NO.</th>
        <th class="views-field views-field-title" scope="col">Title</th>
        <th class="views-field views-field-field-notice-date" scope="col">Notice Date</th>
        <th class="views-field views-field-field-upload-file" scope="col">Download</th>
      </tr></thead>
      <tbody>{rows}
      </tbody>
    </table>
  </div>
  {pager}
</div>"""


def pager(next_href: str | None) -> str:
    if not next_href:
        return '<nav class="pager" role="navigation"><ul class="pager__items"></ul></nav>'
    return f"""<nav class="pager" role="navigation" aria-labelledby="pagination-heading">
    <ul class="pager__items js-pager__items">
      <li class="pager__item pager__item--next">
        <a href="{next_href}" title="Go to next page" rel="next"><span class="visually-hidden">Next page</span>››</a>
      </li>
    </ul>
  </nav>"""


def build_notices() -> None:
    live = soup_of("notices_page0.html")
    view = view_block(live, "div.view-id-notices", keep_rows=10)
    write(NOTICES / "normal_page.html", "Notices", "real JNU /notices markup, first 10 rows + real pager", str(view))

    rows = (
        notice_row(1, "Circular regarding holiday on 11.09.2026",
                   "/sites/default/files/inline-files/CIRCULAR09072026.pdf", "Mon, 07-09-2026")
        + notice_row(2, "Notice without a date cell value",
                     "/sites/default/files/inline-files/NO_DATE.pdf", None)
        + notice_row(3, "Notice with no link at all (text only)", None, "Fri, 04-09-2026")
        + notice_row(4, "Convocation page (HTML, not PDF)", "https://www.jnu.ac.in/convocation", "Thu, 03-09-2026")
    )
    write(NOTICES / "missing_optional_field.html", "Notices", "row 2 has no date, row 3 has no link",
          notices_view(rows))

    changed = """<div class="view view-notices view-id-notices view-display-id-page_1">
  <div class="view-content">
    <div class="views-row notice-card">
      <h3 class="notice-card__title"><a href="/sites/default/files/inline-files/CIRCULAR09072026.pdf">Circular regarding holiday on 11.09.2026</a></h3>
      <span class="notice-card__date">Mon, 07-09-2026</span>
    </div>
    <div class="views-row notice-card">
      <h3 class="notice-card__title"><a href="/sites/default/files/inline-files/commencement.pdf">Commencement of classes</a></h3>
      <span class="notice-card__date">Mon, 31-08-2026</span>
    </div>
  </div>
</div>"""
    write(NOTICES / "changed_card_structure.html", "Notices",
          "hypothetical redesign: table replaced by cards (same view id)", changed)

    empty = soup_of("jnuevents_page1_empty.html").select_one("div.view-id-jnu_events")
    empty_notices = str(empty).replace("view-jnu-events view-id-jnu_events", "view-notices view-id-notices")
    write(NOTICES / "empty_listing.html", "Notices",
          "real Drupal empty state (copied from /jnuevents?page=1, view id renamed)", empty_notices)

    dup_rows = (
        notice_row(1, "Circular regarding holiday on 11.09.2026",
                   "/sites/default/files/inline-files/CIRCULAR09072026.pdf", "Mon, 07-09-2026")
        + notice_row(2, "Circular regarding holiday on 11.09.2026",
                     "/sites/default/files/inline-files/CIRCULAR09072026.pdf", "Mon, 07-09-2026")
        + notice_row(3, "Commencement of classes", "/sites/default/files/inline-files/commencement.pdf",
                     "Mon, 31-08-2026")
    )
    write(NOTICES / "duplicate_item.html", "Notices", "same notice listed twice", notices_view(dup_rows))


def build_events() -> None:
    live = soup_of("jnuevents.html")
    view = view_block(live, "div.view-id-jnu_events", keep_rows=5)
    # make the 5th row point at a node that does not exist -> detail 404 test
    last_link = [tr for tr in view.select("table tr") if tr.find("td")][-1].select_one("td.views-field-title a")
    last_link["href"] = "/node/999999999"
    last_link.string = "Event whose detail page is gone (404 in tests)"
    write(EVENTS / "listing.html", "JNU Events", "real /jnuevents markup, 5 rows; row 5 -> missing node",
          str(view))

    for node in ("159898390", "159897904", "159898442"):
        article = soup_of(f"node_{node}.html").select_one("article.node")
        write(EVENTS / f"detail_{node}.html", "Event", f"real /node/{node} article", str(article))

    write(EVENTS / "detail_broken.html", "Event", "detail page without the expected article",
          "<div class='maintenance'>Site under maintenance</div>")

    archive = view_block(soup_of("events_archive_page0.html"), "div.view-id-jnu_events", keep_rows=5)
    write(EVENTS / "archive_page.html", "JNU Events Archive",
          "real /events-archive markup (only end-date column), 5 rows + real pager", str(archive))


def build_pagination() -> None:
    """3 pages x 5 records. 'Library timing' appears on page 1 AND page 2 (duplicate)."""
    base = "https://www.jnu.ac.in/sites/default/files/inline-files/"
    pages = [
        [("Circular regarding holiday on 11.09.2026", "CIRCULAR09072026.pdf", "Mon, 07-09-2026"),
         ("Add/Drop extension for new students", "AddDrop.pdf", "Mon, 07-09-2026"),
         ("Commencement of UG classes", "commencement.pdf", "Mon, 31-08-2026"),
         ("Hostel allotment list", "hostel.pdf", "Fri, 28-08-2026"),
         ("Revised library timings", "library.pdf", "Thu, 27-08-2026")],
        [("Revised library timings", "library.pdf", "Thu, 27-08-2026"),  # duplicate from page 1
         ("Fee submission schedule", "fees.pdf", "Wed, 26-08-2026"),
         ("PhD viva notification", "viva.pdf", "Tue, 25-08-2026"),
         ("Sports week announcement", "sports.pdf", "Mon, 24-08-2026"),
         ("Scholarship verification", "scholarship.pdf", "Fri, 21-08-2026")],
        [("Anti-ragging committee", "antiragging.pdf", "Thu, 20-08-2026"),
         ("Independence Day celebration", "aug15.pdf", "Wed, 12-08-2026"),
         ("Exam form deadline", "examform.pdf", "Tue, 11-08-2026"),
         ("Campus Wi-Fi maintenance", "wifi.pdf", "Mon, 10-08-2026"),
         ("Library book return drive", "bookreturn.pdf", "Fri, 07-08-2026")],
    ]
    for i, records in enumerate(pages, start=1):
        rows = "".join(notice_row(n, t, base + f, d) for n, (t, f, d) in enumerate(records, start=1 + (i - 1) * 5))
        next_href = f"page_{i + 1}.html" if i < len(pages) else None
        write(PAGINATION / f"page_{i}.html", f"Notices page {i}",
              f"pagination fixture page {i}/3" + ("" if next_href else " (last page, no next link)"),
              notices_view(rows, pager(next_href)))

    # loop trap: next link points back to page 1
    rows = notice_row(1, "Loop trap record", base + "loop.pdf", "Mon, 03-08-2026")
    write(PAGINATION / "loop_page.html", "Loop", "next link points to itself -> must stop (already_visited)",
          notices_view(rows, pager("loop_page.html")))


if __name__ == "__main__":
    build_notices()
    build_events()
    build_pagination()
