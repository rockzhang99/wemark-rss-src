from core.models.article import Article
from sqlalchemy import func
import core.db as db
DB=db.Db(tag="文章清理")
def clean_duplicate_articles(feed_ids=None):
    """
    清理重复的文章

    Args:
        feed_ids: 仅清理这些 feed_id 对应公众号下的重复文章；None 表示全部（管理员）。
    """
    try:
        session = DB.get_session()

        base_query = session.query(Article)
        if feed_ids is not None:
            if not feed_ids:
                return ("没有指定可清理的公众号", 0)
            base_query = base_query.filter(Article.mp_id.in_(feed_ids))
        
        # 查询所有文章的标题，并统计重复的标题
        duplicate_titles = base_query.with_entities(
            Article.title,
            func.count(Article.id).label('count')
        ).group_by(Article.title).having(func.count(Article.id) > 1).all()
        
        # 如果没有重复的标题，直接返回
        if not duplicate_titles:
            return ("没有找到重复的文章", 0)
        
        # 获取所有重复的标题列表
        titles = [item[0] for item in duplicate_titles]
        
        # 查询这些标题对应的所有文章
        articles = base_query.filter(Article.title.in_(titles)).all()
        
        # 用于存储已检查的文章标题和mp_id组合
        seen_articles = set()
        duplicates = []
        
        # 检查重复文章
        for article in articles:
            article_key = (article.title, article.mp_id)
            if article_key in seen_articles:
                duplicates.append(article)
            else:
                seen_articles.add(article_key)
        
        # 删除重复文章
        for duplicate in duplicates:
            print(f"删除重复文章: {duplicate.title}")
            session.delete(duplicate)
        session.commit()
    except:
        session.rollback()
    return (f"已清理 {len(duplicates)} 篇重复文章", len(duplicates))

if __name__ == "__main__":
    result = clean_duplicate_articles()
    print(result)
