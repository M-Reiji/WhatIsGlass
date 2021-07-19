import re
from api.database import db, ma
from sqlalchemy import *
from .answer import Answer
from .user import User
from .categorytag import IndexCategoryTag
import datetime
from flask import abort
from sqlalchemy.orm import relationship
from sqlalchemy.dialects import mysql


class Index(db.Model):
    __tablename__ = "indices"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    index = db.Column(db.String(50), nullable=False)
    questioner = db.Column(db.Integer, nullable=False)
    frequently_used_count = db.Column(db.Integer, nullable=False)
    language_id = db.Column(db.Integer, nullable=False)
    date = db.Column(db.TIMESTAMP, nullable=True)

    def __repr__(self):
        return "<Index %r>" % self.id

    def getIndexList(request_dict):
        # リクエストから取得
        sort = int(request_dict["sort"]) if request_dict["sort"] is not None else 1
        language_id = request_dict["language_id"]
        include_no_answer = (
            int(request_dict["include_no_answer"])
            if request_dict["include_no_answer"] is not ""
            else 1
        )
        keyword = request_dict["keyword"]

        category_tag_id_list = (
            re.findall(r"\d+", request_dict["category_tag_id"])
            if request_dict["category_tag_id"] != ""
            else ""
        )

        category_tag_filter = Index.get_category_tag_filter(category_tag_id_list)

        index_limit = (
            int(request_dict["index_limit"])
            if request_dict["index_limit"] is not ""
            else 300
            if int(request_dict["index_limit"]) > 300
            else 100
        )

        # sortの条件を指定

        sort_terms = (
            "indices.date"
            if sort == 1
            else "indices.frequently_used_count, indices.date"
            if sort == 2
            else "indices.date, answer_count"
            if sort == 3
            else "indices.date"
        )

        answer_count = Index.get_answer_count()
        best_answer = Index.get_best_answer()

        index_list = db.session.query(
            Index.id,
            Index.index,
            User.username,
            Index.frequently_used_count,
            Index.language_id,
            Index.date,
            answer_count.c.answer_count.label("answer_count"),
            best_answer.c.best_answer,
        )

        if include_no_answer == 2:
            index_list = index_list.join(
                best_answer, Index.id == best_answer.c.index_id
            )
        else:
            index_list = index_list.outerjoin(
                best_answer, Index.id == best_answer.c.index_id
            )

        index_list = index_list.filter(
            Index.index.contains(f"{keyword}"),
            Index.language_id == language_id,
            User.id == Index.questioner,
            Index.id == answer_count.c.index_id,
            Index.id == category_tag_filter.c.index_id,
        )

        if include_no_answer == 3:
            index_list = index_list.filter(answer_count.c.answer_count == 0)

        index_list = (
            index_list.distinct(Index.id)
            .order_by(desc(text(f"{sort_terms}")))
            .limit(index_limit)
        )

        print(
            index_list.statement.compile(
                dialect=mysql.dialect(), compile_kwargs={"literal_binds": True}
            )
        )
        if index_list == null:
            return []
        else:
            return index_list

    def getIndex(index_id):

        answer_count = Index.get_answer_count()
        best_answer = Index.get_best_answer()

        index = (
            db.session.query(
                Index.id,
                Index.index,
                User.username,
                Index.frequently_used_count,
                Index.language_id,
                Index.date,
                answer_count.c.answer_count.label("answer_count"),
                best_answer.c.best_answer,
            )
            .outerjoin(best_answer, Index.id == best_answer.c.index_id)
            .filter(
                User.id == Index.questioner,
                Index.id == answer_count.c.index_id,
                Index.id == index_id,
            )
            .all()
        )

        if index == null:
            return []
        else:
            return index

    def getUserIndexList(request_dict):
        # リクエストから取得
        sort = int(request_dict["sort"]) if request_dict["sort"] is not None else 1
        language_id = request_dict["language_id"]
        include_no_answer = (
            int(request_dict["include_no_answer"])
            if request_dict["include_no_answer"] is not ""
            else 1
        )
        user_id = request_dict["user_id"]

        index_limit = (
            int(request_dict["index_limit"])
            if request_dict["index_limit"] is not ""
            else 300
            if int(request_dict["index_limit"]) > 300
            else 100
        )

        # sortの条件を指定
        sort_terms = (
            "indices.date"
            if sort == 1
            else "indices.frequently_used_count, indices.date"
            if sort == 2
            else "indices.date, answer_count"
            if sort == 3
            else "indices.date"
        )

        answer_count = Index.get_answer_count()
        best_answer = Index.get_best_answer()

        index_list = db.session.query(
            Index.id,
            Index.index,
            User.username,
            Index.frequently_used_count,
            Index.language_id,
            Index.date,
            answer_count.c.answer_count.label("answer_count"),
            best_answer.c.best_answer,
        )

        if include_no_answer == 2:
            index_list = index_list.join(
                best_answer, Index.id == best_answer.c.index_id
            )
        else:
            index_list = index_list.outerjoin(
                best_answer, Index.id == best_answer.c.index_id
            )

        index_list = index_list.filter(
            Index.index.contains(f"{keyword}"),
            Index.language_id == language_id,
            User.id == Index.questioner,
            User.id == user_id,
            Index.id == answer_count.c.index_id,
        )

        if include_no_answer == 3:
            index_list = index_list.filter(answer_count.c.answer_count == 0)

        index_list = (
            index_list.distinct(Index.id)
            .order_by(desc(text(f"{sort_terms}")))
            .limit(index_limit)
            .all()
        )

        if index_list == null:
            return []
        else:
            return index_list

    # 回答者数が少ない見出しを取得
    def get_unpopular_question(request_dict):

        if request_dict["language_ids"] != "":
            language_id_filters = []
            language_id_list = re.findall(r"\d+", request_dict["language_ids"])
            for language_id in language_id_list:
                language_id_filters.append(Index.language_id == language_id)
        else:
            return abort(400, {"message": "language_ids is required"})

        is_random = request_dict["is_random"] if request_dict["is_random"] != "" else 1

        index_limit = (
            int(request_dict["index_limit"])
            if request_dict["index_limit"] is not ""
            else 30
            if int(request_dict["index_limit"]) > 30
            else 3
        )

        answer_count = Index.get_answer_count()
        best_answer = Index.get_best_answer()

        index_list = db.session.query(
            Index.id,
            Index.index,
            User.username,
            Index.frequently_used_count,
            Index.language_id,
            Index.date,
            answer_count.c.answer_count.label("answer_count"),
            best_answer.c.best_answer,
        )

        index_list = index_list.outerjoin(
            best_answer, Index.id == best_answer.c.index_id
        )

        index_list = index_list.filter(
            or_(*language_id_filters),
            User.id == Index.questioner,
            Index.id == answer_count.c.index_id,
            answer_count.c.answer_count == 0,
        )

        index_list = index_list.distinct(Index.id)

        print(is_random)
        if is_random == "2":
            index_list = index_list.order_by(func.rand())

        index_list = index_list.limit(index_limit).all()

        return index_list

    def registIndex(indices):
        record = Index(
            id=0,
            index=indices["index"],
            questioner=indices["questioner"],
            frequently_used_count=0,
            language_id=indices["language_id"],
            date=datetime.datetime.now(),
        )

        db.session.add(record)
        db.session.flush()
        db.session.commit()

        response = db.session.execute(
            "SELECT * from indices WHERE id = last_insert_id();"
        )

        return response

    def get_answer_count():
        # 回答者数を取得するためのクエリ
        answer_count = (
            db.session.query(
                Index.id.label("index_id"),
                func.count(Answer.index_id).label("answer_count"),
            )
            .outerjoin(Answer, Index.id == Answer.index_id)
            .group_by(Index.id)
            .subquery("answer_count")
        )

        return answer_count

    def get_best_answer():
        # ベストアンサーを一覧取得するためのクエリ
        max_informative = (
            db.session.query(
                Answer.index_id, func.max(Answer.informative_count).label("max_count")
            )
            .group_by(Answer.index_id)
            .subquery("max_informative")
        )

        best_answer = (
            db.session.query(
                Answer.index_id, func.any_value(Answer.definition).label("best_answer")
            )
            .join(
                max_informative,
                Answer.index_id == max_informative.c.index_id,
            )
            .filter(Answer.informative_count == max_informative.c.max_count)
            .group_by(Answer.index_id)
            .having(func.max(Answer.date))
            .subquery("best_answer")
        )

        return best_answer

    def get_category_tag_filter(category_tag_id_list):

        count = False
        for category_tag_id in category_tag_id_list:
            if count is False:
                filter_index_id = (
                    db.session.query(IndexCategoryTag.index_id.label("index_id"))
                    .filter(
                        IndexCategoryTag.category_tag_id == category_tag_id,
                    )
                    .subquery("filter_index_id")
                )
                count = True
            else:
                filter_index_id = (
                    db.session.query(IndexCategoryTag.index_id.label("index_id"))
                    .filter(
                        IndexCategoryTag.index_id == filter_index_id.c.index_id,
                        IndexCategoryTag.category_tag_id == category_tag_id,
                    )
                    .subquery("filter_index_id")
                )

        return filter_index_id


class IndexSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Index
        load_instance = True
        fields = (
            "id",
            "index",
            "questioner",
            "language_id",
            "frequently_used_count",
            "date",
            "username",
            "index_id",
            "definition",
            "origin",
            "note",
            "informative_count",
            "best_answer",
            "answer_count",
            "categorytags",
        )
