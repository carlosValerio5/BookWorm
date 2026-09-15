from bookworm.crawler.sources.blog_pages import BLOG_PAGES_SOURCE
from bookworm.crawler.sources.commons_categories import COMMONS_CATEGORIES_SOURCE
from bookworm.crawler.sources.openverse_photos import OPENVERSE_PHOTOS_SOURCE

SOURCES_BY_NAME = {
    source.name: source for source in (OPENVERSE_PHOTOS_SOURCE, BLOG_PAGES_SOURCE, COMMONS_CATEGORIES_SOURCE)
}
