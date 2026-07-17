
import core.wx as wx 
import core.db as db
from core.config import DEBUG,cfg
from core.models.article import Article

DB=db.Db(tag="文章采集API")

def UpdateArticle(art:dict,check_exist=True):
    mps_count=0
    if DEBUG:
        # DB.delete_article(art)
        pass
    if  DB.add_article(art,check_exist=check_exist):
        mps_count=mps_count+1
        # 混合架构(改动036) 阶段2：新文章落库后增量推送到云端
        try:
            from core.uploader import uploader
            uploader.enqueue_article(art.get('mp_id'), art)
        except Exception:
            pass
        return True
    return False
def Update_Over(data=None):
    print("更新完成")
    pass