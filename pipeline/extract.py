"""Extract SECOP II contracts from the datos.gov.co Socrata API, page by page."""
from __future__ import annotations

import logging
import time
from datetime import date
from typing import Iterator

import requests

from .config import settings

log = logging.getLogger(__name__)


def build_params(since: date, until: date | None, limit: int, offset: int) -> dict:
    where = f"fecha_de_firma >= '{since.isoformat()}T00:00:00'"
    if until:
        where += f" AND fecha_de_firma < '{until.isoformat()}T00:00:00'"
    # Ordering by :id gives stable pagination even while the dataset is being updated.
    return {"$where": where, "$order": ":id", "$limit": limit, "$offset": offset}


def _get(session: requests.Session, params: dict, retries: int = 4) -> list[dict]:
    for attempt in range(retries):
        try:
            resp = session.get(settings.dataset_url, params=params, timeout=settings.request_timeout)
            if resp.status_code == 429 or resp.status_code >= 500:
                raise requests.HTTPError(f"HTTP {resp.status_code}", response=resp)
            resp.raise_for_status()
            return resp.json()
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as exc:
            if attempt == retries - 1:
                raise
            wait = 2 ** attempt
            log.warning("request failed (%s), retrying in %ss", exc, wait)
            time.sleep(wait)
    return []  # unreachable


def fetch_contracts(since: date, until: date | None = None, max_rows: int | None = None) -> Iterator[list[dict]]:
    """Yield pages of raw records signed on/after `since` (and before `until`, if given)."""
    session = requests.Session()
    if settings.app_token:
        session.headers["X-App-Token"] = settings.app_token
    offset, total = 0, 0
    while True:
        limit = settings.page_size if max_rows is None else min(settings.page_size, max_rows - total)
        if limit <= 0:
            break
        page = _get(session, build_params(since, until, limit, offset))
        if not page:
            break
        total += len(page)
        log.info("fetched %s rows (total %s)", len(page), total)
        yield page
        if len(page) < limit:
            break
        offset += limit
