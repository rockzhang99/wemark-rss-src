import os
import sys
from core.config import cfg

# 程序根目录: frozen 态资源在 sys._MEIPASS (_internal/), dev 态在 views/ 的上一级(工程根)。
# 用绝对路径解析模板, 兼容开发态与 PyInstaller 冻结态(改动044修复 './public' 找不到)。
if getattr(sys, 'frozen', False):
    _ROOT = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
else:
    _ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Config:
    base_path = os.path.join(_ROOT, "public")
    # 模板路径(基于程序根绝对路径)
    public_dir = os.path.join(base_path, "templates")
    home_template = os.path.join(public_dir, "home.html")
    mps_template = os.path.join(public_dir, "mps.html")
    tags_template = os.path.join(public_dir, "tags.html")
    tags_articles_template = os.path.join(public_dir, "tags_articles.html")
    article_template = os.path.join(public_dir, "article.html")
    article_detail_template = os.path.join(public_dir, "article_detail.html")
    article_detail_print_template = os.path.join(public_dir, "print.html")
    articles_template = os.path.join(public_dir, "articles.html")
    site={
        "name": cfg.get("site.name", "WemarkRss"),
        "description": cfg.get("site.description", "A WeChat Official Account RSS Reader"), 
        "keywords": cfg.get("site.keywords", "WemarkRss,RSS,微信公众号,RSS订阅,RSS阅读器,RSS订阅助手,RSS订阅器,RSS订阅器,RSS订阅器,RSS订阅器"),
        "logo": cfg.get("site.logo", "/static/logo.svg"),
        "favicon": cfg.get("site.favicon", "/static/logo.svg"),
        "author": cfg.get("site.author", "WemarkRss Team"),
        "copyright": cfg.get("site.copyright", "© 2024 WemarkRss Team"),
    }
base = Config()