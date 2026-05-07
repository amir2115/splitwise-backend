from __future__ import annotations

from fastapi.testclient import TestClient

from app import main as main_api
from app.core.config import get_settings


def admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "panel_admin", "password": "super-secret"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_category_and_author(client: TestClient, headers: dict[str, str]) -> None:
    category = client.post(
        "/api/v1/admin/categories",
        headers=headers,
        json={"slug": "travel-split", "name": "تقسیم هزینه سفر", "display_order": 1},
    )
    assert category.status_code == 201
    author = client.post(
        "/api/v1/admin/authors",
        headers=headers,
        json={"slug": "dongino-editorial", "name": "تیم محتوای دنگینو", "role": "Editorial"},
    )
    assert author.status_code == 201


def article_payload(*, slug: str = "taghsim-hazine-safar", status: str = "published", related_slugs: list[str] | None = None) -> dict:
    return {
        "slug": slug,
        "status": status,
        "category_slug": "travel-split",
        "author_slug": "dongino-editorial",
        "title": "چطور هزینه سفر را بین دوستان تقسیم کنیم؟ راهنمای کامل با مثال عددی",
        "summary": "راهنمای کامل تقسیم هزینه سفر با مثال عددی.",
        "tldr": "خرج‌ها را ثبت کنید و تسویه را بهینه انجام دهید.",
        "hero_icon": "✈️",
        "hero_image_url": None,
        "reading_minutes": 9,
        "published_at": "2026-04-30T10:00:00Z",
        "audience": ["گروه‌های دوستانه", "هم‌سفرها"],
        "body": [
            {"kind": "heading", "level": 2, "id": "why-matters", "text": "چرا مهم است؟", "eyebrow": "۰۱"},
            {"kind": "prose", "paragraphs": ["خرج سفر اگر همان لحظه ثبت شود، تسویه ساده‌تر می‌شود."]},
            {"kind": "list", "ordered": True, "items": ["خرج را ثبت کن", "پرداخت‌کننده را مشخص کن"]},
            {"kind": "callout", "variant": "tip", "title": "نکته", "body": "ثبت لحظه‌ای بهتر از محاسبه آخر سفر است."},
            {
                "kind": "scenario",
                "title": "سفر چهار نفره",
                "intro": "هر نفر یک خرج پرداخت کرده است.",
                "rows": [{"label": "اقامت", "value": "۲٬۴۰۰٬۰۰۰ تومان", "hint": "پرداخت‌کننده: سارا"}],
                "summary": {"label": "سهم هر نفر", "value": "۶۰۰٬۰۰۰ تومان"},
                "footnote": "تسویه با یک تراکنش بسته می‌شود.",
            },
            {
                "kind": "comparison",
                "title": "مقایسه روش‌ها",
                "options": [
                    {"label": "اکسل", "pros": ["انعطاف‌پذیر"], "cons": ["دستی"]},
                    {"label": "دنگینو", "tag": "پیشنهادی", "pros": ["خودکار"], "cons": [], "recommended": True},
                ],
            },
            {"kind": "steps", "steps": [{"title": "گروه بساز", "body": "برای سفر یک گروه جدید بساز."}]},
            {
                "kind": "inline-cta",
                "variant": "soft",
                "title": "شروع ثبت خرج گروهی",
                "body": "از نسخه وب استفاده کن.",
                "primary": {"label": "ورود به نسخه وب", "href": "https://pwa.splitwise.ir"},
            },
            {
                "kind": "faq",
                "title": "سوالات متداول",
                "items": [{"question": "آیا همه باید اپ نصب کنند؟", "answer": "نه، نسخه وب هم کافی است."}],
            },
        ],
        "related_slugs": related_slugs or [],
        "seo": {
            "meta_title": "چطور هزینه سفر را بین دوستان تقسیم کنیم؟ | دنگینو",
            "meta_description": "راهنمای کامل تقسیم هزینه سفر با مثال عددی.",
            "canonical_url": f"https://splitwise.ir/articles/{slug}/",
            "og_image_url": None,
        },
    }


def test_admin_can_create_article_with_all_blocks_and_public_detail_expands_it(client: TestClient) -> None:
    headers = admin_headers(client)
    create_category_and_author(client, headers)

    response = client.post("/api/v1/admin/articles", headers=headers, json=article_payload())

    assert response.status_code == 201
    created = response.json()
    assert created["slug"] == "taghsim-hazine-safar"
    assert created["toc"] == [{"id": "why-matters", "title": "چرا مهم است؟"}]
    assert created["body"][-1]["kind"] == "faq"

    public = client.get("/api/v1/articles/taghsim-hazine-safar")
    assert public.status_code == 200
    payload = public.json()
    assert payload["category"]["name"] == "تقسیم هزینه سفر"
    assert payload["author"]["name"] == "تیم محتوای دنگینو"
    assert payload["hero_image_url"] is None
    assert payload["seo"]["canonical_url"] == "https://splitwise.ir/articles/taghsim-hazine-safar/"


def test_public_list_and_sitemap_include_only_published_articles(client: TestClient) -> None:
    headers = admin_headers(client)
    create_category_and_author(client, headers)
    published = client.post("/api/v1/admin/articles", headers=headers, json=article_payload(slug="published-one", status="published"))
    draft = client.post("/api/v1/admin/articles", headers=headers, json=article_payload(slug="draft-one", status="draft"))
    assert published.status_code == 201
    assert draft.status_code == 201

    listing = client.get("/api/v1/articles")
    assert listing.status_code == 200
    assert [item["slug"] for item in listing.json()["items"]] == ["published-one"]
    assert listing.json()["items"][0]["hero_image_url"] is None

    sitemap = client.get("/api/v1/articles/sitemap")
    assert sitemap.status_code == 200
    assert [item["slug"] for item in sitemap.json()["items"]] == ["published-one"]


def test_related_articles_are_expanded_in_detail(client: TestClient) -> None:
    headers = admin_headers(client)
    create_category_and_author(client, headers)
    base = client.post("/api/v1/admin/articles", headers=headers, json=article_payload(slug="base-article"))
    assert base.status_code == 201
    related = client.post(
        "/api/v1/admin/articles",
        headers=headers,
        json=article_payload(slug="with-related", related_slugs=["base-article"]),
    )
    assert related.status_code == 201

    detail = client.get("/api/v1/articles/with-related")
    assert detail.status_code == 200
    assert detail.json()["related"][0]["slug"] == "base-article"


def test_rejects_duplicate_heading_ids_and_missing_related_slug(client: TestClient) -> None:
    headers = admin_headers(client)
    create_category_and_author(client, headers)
    duplicate_heading = article_payload()
    duplicate_heading["body"].append({"kind": "heading", "level": 2, "id": "why-matters", "text": "تکراری"})
    response = client.post("/api/v1/admin/articles", headers=headers, json=duplicate_heading)
    assert response.status_code == 422

    missing_related = client.post(
        "/api/v1/admin/articles",
        headers=headers,
        json=article_payload(slug="missing-related", related_slugs=["not-found"]),
    )
    assert missing_related.status_code == 400
    assert missing_related.json()["error"]["code"] == "article_related_not_found"


def test_archive_article_returns_gone_for_public_detail(client: TestClient) -> None:
    headers = admin_headers(client)
    create_category_and_author(client, headers)
    created = client.post("/api/v1/admin/articles", headers=headers, json=article_payload())
    assert created.status_code == 201
    article_id = created.json()["id"]

    archived = client.delete(f"/api/v1/admin/articles/{article_id}", headers=headers)
    assert archived.status_code == 204

    public = client.get("/api/v1/articles/taghsim-hazine-safar")
    assert public.status_code == 410
    assert public.json()["error"]["code"] == "article_archived"


def test_admin_can_upload_article_hero_image_and_public_detail_expands_url(client: TestClient, tmp_path, monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "article_image_upload_dir", str(tmp_path))
    monkeypatch.setattr(settings, "article_image_public_base_url", "https://api.splitwise.ir")
    monkeypatch.setattr(main_api.settings, "article_image_upload_dir", str(tmp_path))
    headers = admin_headers(client)
    create_category_and_author(client, headers)
    created = client.post("/api/v1/admin/articles", headers=headers, json=article_payload())
    assert created.status_code == 201
    article_id = created.json()["id"]

    response = client.post(
        f"/api/v1/admin/articles/{article_id}/hero-image",
        headers=headers,
        files={"file": ("cover.webp", b"webp-image-content", "image/webp")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "filename": "taghsim-hazine-safar.webp",
        "stored_path": str(tmp_path / "taghsim-hazine-safar.webp"),
        "hero_image_url": "https://api.splitwise.ir/files/articles/taghsim-hazine-safar.webp",
    }
    assert (tmp_path / "taghsim-hazine-safar.webp").read_bytes() == b"webp-image-content"

    public = client.get("/api/v1/articles/taghsim-hazine-safar")
    assert public.status_code == 200
    payload = public.json()
    assert payload["hero_image_url"] == "https://api.splitwise.ir/files/articles/taghsim-hazine-safar.webp"
    assert payload["seo"]["og_image_url"] == "https://api.splitwise.ir/files/articles/taghsim-hazine-safar.webp"

    download = client.get("/files/articles/taghsim-hazine-safar.webp")
    assert download.status_code == 200
    assert download.content == b"webp-image-content"
    assert download.headers["content-type"] == "image/webp"


def test_upload_article_hero_image_keeps_existing_og_image(client: TestClient, tmp_path, monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "article_image_upload_dir", str(tmp_path))
    monkeypatch.setattr(settings, "article_image_public_base_url", "https://api.splitwise.ir")
    monkeypatch.setattr(main_api.settings, "article_image_upload_dir", str(tmp_path))
    headers = admin_headers(client)
    create_category_and_author(client, headers)
    payload = article_payload()
    payload["seo"]["og_image_url"] = "https://cdn.example.com/custom-og.webp"
    created = client.post("/api/v1/admin/articles", headers=headers, json=payload)
    assert created.status_code == 201

    response = client.post(
        f"/api/v1/admin/articles/{created.json()['id']}/hero-image",
        headers=headers,
        files={"file": ("cover.png", b"png-content", "image/png")},
    )
    assert response.status_code == 200

    public = client.get("/api/v1/articles/taghsim-hazine-safar")
    assert public.status_code == 200
    assert public.json()["hero_image_url"] == "https://api.splitwise.ir/files/articles/taghsim-hazine-safar.png"
    assert public.json()["seo"]["og_image_url"] == "https://cdn.example.com/custom-og.webp"


def test_upload_article_hero_image_requires_admin_and_rejects_invalid_filenames(client: TestClient, tmp_path, monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "article_image_upload_dir", str(tmp_path))
    monkeypatch.setattr(main_api.settings, "article_image_upload_dir", str(tmp_path))
    headers = admin_headers(client)
    create_category_and_author(client, headers)
    created = client.post("/api/v1/admin/articles", headers=headers, json=article_payload())
    assert created.status_code == 201
    article_id = created.json()["id"]

    unauthorized = client.post(
        f"/api/v1/admin/articles/{article_id}/hero-image",
        files={"file": ("cover.webp", b"content", "image/webp")},
    )
    assert unauthorized.status_code == 401

    invalid_extension = client.post(
        f"/api/v1/admin/articles/{article_id}/hero-image",
        headers=headers,
        files={"file": ("cover.gif", b"content", "image/gif")},
    )
    assert invalid_extension.status_code == 400
    assert invalid_extension.json()["error"]["code"] == "invalid_article_image"

    path_traversal = client.post(
        f"/api/v1/admin/articles/{article_id}/hero-image",
        headers=headers,
        files={"file": ("../cover.webp", b"content", "image/webp")},
    )
    assert path_traversal.status_code == 400
    assert path_traversal.json()["error"]["code"] == "invalid_article_image"
