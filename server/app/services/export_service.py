# server/app/services/export_service.py

import csv
import io
import json
import logging
from datetime import datetime
from typing import List, Optional

from flask import current_app

from app.models.link import Link
from app.utils.base_url import get_public_base_url

logger = logging.getLogger(__name__)


class ExportService:

    @staticmethod
    def export_links_json(links: List[Link], include_stats: bool = True) -> dict:
        base_url = get_public_base_url()

        export_data = {
            "exported_at": datetime.utcnow().isoformat(),
            "count": len(links),
            "links": []
        }

        for link in links:
            link_data = {
                "original_url": link.original_url,
                "title": link.title,
                "notes": link.notes,
                "link_type": link.link_type.value,
                "created_at": link.created_at.isoformat(),
            }

            if link.slug:
                link_data["short_url"] = f"{base_url}/{link.slug}"
                link_data["slug"] = link.slug

            if link.folder:
                link_data["folder"] = link.folder.name

            if link.tags:
                link_data["tags"] = [t.name for t in link.tags]

            if link.category:
                link_data["category"] = link.category.name

            if include_stats:
                link_data["clicks"] = link.clicks
                link_data["is_active"] = link.is_active
                link_data["is_broken"] = link.is_broken

            if link.expires_at:
                link_data["expires_at"] = link.expires_at.isoformat()

            export_data["links"].append(link_data)

        return export_data

    @staticmethod
    def export_links_csv(links: List[Link]) -> str:
        base_url = get_public_base_url()

        output = io.StringIO()
        fieldnames = [
            "original_url",
            "short_url",
            "title",
            "notes",
            "link_type",
            "folder",
            "tags",
            "clicks",
            "is_active",
            "created_at",
            "expires_at"
        ]

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for link in links:
            row = {
                "original_url": link.original_url,
                "short_url": f"{base_url}/{link.slug}" if link.slug else "",
                "title": link.title or "",
                "notes": (link.notes or "").replace("\n", " ").replace("\r", "")[:500],
                "link_type": link.link_type.value,
                "folder": link.folder.name if link.folder else "",
                "tags": ", ".join(t.name for t in link.tags) if link.tags else "",
                "clicks": link.clicks,
                "is_active": "Yes" if link.is_active else "No",
                "created_at": link.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "expires_at": link.expires_at.strftime("%Y-%m-%d %H:%M:%S") if link.expires_at else "",
            }
            writer.writerow(row)

        return output.getvalue()

    @staticmethod
    def export_links_html(links: List[Link], title: str = "My Savlink Collection") -> str:
        base_url = get_public_base_url()

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
        h1 {{ color: #1a1a2e; border-bottom: 2px solid #1a1a2e; padding-bottom: 10px; }}
        .link {{ background: white; padding: 15px; margin: 10px 0; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .link h3 {{ margin: 0 0 8px 0; }}
        .link a {{ color: #1a1a2e; text-decoration: none; }}
        .link a:hover {{ text-decoration: underline; }}
        .link .url {{ color: #666; font-size: 14px; word-break: break-all; }}
        .link .meta {{ color: #888; font-size: 12px; margin-top: 8px; }}
        .link .tags {{ margin-top: 8px; }}
        .link .tag {{ display: inline-block; background: #e9ecef; padding: 2px 8px; border-radius: 4px; font-size: 12px; margin-right: 4px; }}
        .footer {{ text-align: center; color: #888; margin-top: 30px; font-size: 12px; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p>Exported on {datetime.utcnow().strftime("%B %d, %Y")} • {len(links)} links</p>
"""

        for link in links:
            short_url = f"{base_url}/{link.slug}" if link.slug else None
            display_title = link.title or link.original_url[:60]

            html += f"""
    <div class="link">
        <h3><a href="{link.original_url}" target="_blank">{display_title}</a></h3>
        <div class="url">{link.original_url}</div>
"""
            if short_url:
                html += f'        <div class="url">Short: <a href="{short_url}">{short_url}</a></div>\n'

            if link.notes:
                html += f'        <p>{link.notes[:200]}{"..." if len(link.notes or "") > 200 else ""}</p>\n'

            if link.tags:
                html += '        <div class="tags">'
                for tag in link.tags:
                    html += f'<span class="tag">{tag.name}</span>'
                html += '</div>\n'

            html += f'        <div class="meta">Added: {link.created_at.strftime("%Y-%m-%d")} • Clicks: {link.clicks}</div>\n'
            html += '    </div>\n'

        html += """
    <div class="footer">
        <p>Exported from <a href="https://savlink.vercel.app">Savlink</a></p>
    </div>
</body>
</html>
"""
        return html

    @staticmethod
    def export_bookmarks_html(links: List[Link]) -> str:
        base_url = get_public_base_url()

        html = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<!-- This is an automatically generated file. -->
<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
<TITLE>Bookmarks</TITLE>
<H1>Bookmarks</H1>
<DL><p>
    <DT><H3>Savlink Export</H3>
    <DL><p>
"""

        folders = {}
        no_folder = []

        for link in links:
            if link.folder:
                if link.folder.name not in folders:
                    folders[link.folder.name] = []
                folders[link.folder.name].append(link)
            else:
                no_folder.append(link)

        for folder_name, folder_links in folders.items():
            html += f'        <DT><H3>{folder_name}</H3>\n        <DL><p>\n'
            for link in folder_links:
                title = link.title or link.original_url[:60]
                add_date = int(link.created_at.timestamp())
                html += f'            <DT><A HREF="{link.original_url}" ADD_DATE="{add_date}">{title}</A>\n'
            html += '        </DL><p>\n'

        for link in no_folder:
            title = link.title or link.original_url[:60]
            add_date = int(link.created_at.timestamp())
            html += f'        <DT><A HREF="{link.original_url}" ADD_DATE="{add_date}">{title}</A>\n'

        html += """    </DL><p>
</DL><p>
"""
        return html

    @staticmethod
    def import_bookmarks_html(html_content: str, user_id: str) -> dict:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, 'html.parser')

        imported = 0
        skipped = 0
        errors = []

        for a_tag in soup.find_all('a'):
            href = a_tag.get('href', '')
            title = a_tag.get_text(strip=True)

            if not href or not href.startswith(('http://', 'https://')):
                skipped += 1
                continue

            try:
                from app.services.link_service import LinkService
                from app.models.link import LinkType

                link, error, _ = LinkService.create_link(
                    user_id=user_id,
                    original_url=href,
                    link_type=LinkType.SAVED,
                    title=title[:255] if title else None,
                    fetch_metadata=False
                )

                if link:
                    imported += 1
                else:
                    if "already have" in (error or ""):
                        skipped += 1
                    else:
                        errors.append({"url": href[:100], "error": error})

            except Exception as e:
                errors.append({"url": href[:100], "error": str(e)})

        return {
            "imported": imported,
            "skipped": skipped,
            "errors": errors[:10]
        }