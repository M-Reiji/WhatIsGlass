from os import kill
from flask import Blueprint, request, make_response, jsonify, session, abort
from api.models import User
from api.models import (
    Index,
    IndexSchema,
    IndexCategoryTag,
    IndexCategorytagSchema,
    IndexUserCommunityTag,
)
from flask_jwt_extended import jwt_required, current_user
from ..token import jwt
import json

# ルーティング設定
question_router = Blueprint("question_router", __name__)


@question_router.errorhandler(400)
def error_handler(err):
    res = jsonify({"error": {"message": err.description["message"]}, "code": err.code})
    return res, err.code


# 見出し一覧API
@question_router.route("/question", methods=["GET"])
@jwt_required(optional=True)
def getIndexList():

    try:
        contents = request.args

        # リクエストの初期値
        request_dict = {
            "sort": 1,
            "include_no_answer": 1,
            "keyword": "",
            "category_tag_id": "",
            "index_limit": 100,
        }

        if contents.get("sort") is not None and contents.get("sort") != "":
            request_dict["sort"] = contents.get("sort")

        if (
            contents.get("include_no_answer") is not None
            and contents.get("include_no_answer") != ""
        ):
            request_dict["include_no_answer"] = contents.get("include_no_answer")

        if contents.get("keyword") is not None and contents.get("keyword") != "":
            request_dict["keyword"] = contents.get("keyword")

        if (
            contents.get("category_tag_id") is not None
            and contents.get("category_tag_id") != ""
        ):
            request_dict["category_tag_id"] = contents.get("category_tag_id")

        if (
            contents.get("index_limit") is not None
            and contents.get("index_limit") != ""
        ):
            request_dict["index_limit"] = contents.get("index_limit")

        if (
            contents.get("language_id") is not None
            and contents.get("language_id") != ""
        ):
            request_dict["language_id"] = contents.get("language_id")
        else:
            abort(400, {"message": "language_id is required"})

        indices = Index.getIndexList(request_dict)
        index_schema = IndexSchema(many=True)
        indices_list = index_schema.dump(indices)

    except ValueError:
        abort(400, {"message": "get failed"})

    return make_response(
        jsonify({"code": 200, "indices": merge_indices_categorytags(indices_list)})
    )


# 見出し取得API
@question_router.route("/specific-question", methods=["GET"])
@jwt_required(optional=True)
def getIndex():

    try:
        contents = request.args

        if contents.get("index_id") is None or contents.get("index_id") == "":
            abort(400, {"message": "index_id is required"})

        indices = Index.getIndex(contents.get("index_id"))
        index_schema = IndexSchema(many=True)
        indices_list = index_schema.dump(indices)

    except ValueError:
        abort(400, {"message": "get failed"})

    return make_response(
        jsonify({"code": 200, "indices": merge_indices_categorytags(indices_list)})
    )


# 質問投稿API
@question_router.route("/question", methods=["POST"])
@jwt_required()
def registIndex():

    # jsonデータを取得する
    jsonData = json.dumps(request.json)
    indexData = json.loads(jsonData)

    if (
        indexData is None
        or not "index" in indexData
        or not "language_id" in indexData
        or indexData["index"] == ""
        or indexData["language_id"] == ""
    ):
        abort(400, {"message": "parameter is a required"})

    if current_user is not None:
        indexData["questioner"] = current_user.id
    else:
        abort(400, {"message": "Login required"})

    try:
        index = Index.registIndex(indexData)
        index_schema = IndexSchema(many=True)
    except ValueError:
        abort(400, {"message": "post failed"})

    return make_response(jsonify({"code": 201, "index": index_schema.dump(index)[0]}))


# ユーザー見出し一覧API
@question_router.route("user/question-list", methods=["GET"])
@jwt_required()
def getUserIndexList():

    try:
        contents = request.args

        # リクエストの初期値
        request_dict = {
            "sort": 1,
            "include_no_answer": 1,
            "index_limit": 100,
        }

        if current_user is not None:
            request_dict["user_id"] = current_user.id
        else:
            abort(400, {"message": "Login required"})

        if contents.get("sort") is not None and contents.get("sort") != "":
            request_dict["sort"] = contents.get("sort")

        if (
            contents.get("include_no_answer") is not None
            and contents.get("include_no_answer") != ""
        ):
            request_dict["include_no_answer"] = contents.get("include_no_answer")

        if (
            contents.get("index_limit") is not None
            and contents.get("index_limit") != ""
        ):
            request_dict["index_limit"] = contents.get("index_limit")

        if (
            contents.get("language_id") is not None
            and contents.get("language_id") != ""
        ):
            request_dict["language_id"] = contents.get("language_id")
        else:
            abort(400, {"message": "language_id is required"})

        indices = Index.getUserIndexList(request_dict)
        index_schema = IndexSchema(many=True)
        index_list = index_schema.dump(indices)

    except ValueError:
        abort(400, {"message": "get failed"})

    return make_response(
        jsonify({"code": 200, "indices": merge_indices_categorytags(index_list)[0]})
    )


# 要回答見出し取得API
@question_router.route("/unpopular-question", methods=["GET"])
@jwt_required(optional=True)
def getUnpopularIndexList():

    try:
        contents = request.args

        # リクエストの初期値
        request_dict = {
            "index_limit": 3,
            "is_random": 1,
        }

        if (
            contents.get("index_limit") is not None
            and contents.get("index_limit") != ""
        ):
            request_dict["index_limit"] = contents.get("index_limit")

        if contents.get("is_random") is not None and contents.get("is_random") != "":
            request_dict["is_random"] = contents.get("is_random")

        if (
            contents.get("language_ids") is not None
            and contents.get("language_ids") != ""
        ):
            request_dict["language_ids"] = contents.get("language_ids")
        else:
            abort(400, {"message": "language_ids is required"})

        indices = Index.get_unpopular_question(request_dict)
        index_schema = IndexSchema(many=True)
        indices_list = index_schema.dump(indices)

    except ValueError:
        abort(400, {"message": "get failed"})

    return make_response(
        jsonify({"code": 200, "indices": merge_indices_categorytags(indices_list)})
    )


# 見出しよく使うカウントアップAPI
@question_router.route("/count-up-frequently-used", methods=["POST"])
@jwt_required()
def countupFrequently():

    # jsonデータを取得する
    jsonData = json.dumps(request.json)
    indexData = json.loads(jsonData)

    if indexData is None or not "index_id" in indexData or indexData["index_id"] == "":
        abort(400, {"message": "parameter is a required"})

    if current_user is not None:
        indexData["user_id"] = current_user.id
    else:
        abort(400, {"message": "Login required"})

    try:
        index = IndexUserCommunityTag.countupCommunityTag(indexData)
        if index != False:
            index_schema = IndexSchema(many=True)
            index_list = index_schema.dump(index)
        else:
            abort(400, {"message": "count failed"})
    except ValueError:
        abort(400, {"message": "count failed"})

    return make_response(
        jsonify({"code": 201, "indices": merge_indices_categorytags(index_list)})
    )


# 見出しよく使うカウントダウンAPI
@question_router.route("/count-down-frequently-used", methods=["POST"])
@jwt_required()
def countdownFrequently():

    # jsonデータを取得する
    jsonData = json.dumps(request.json)
    indexData = json.loads(jsonData)

    if indexData is None or not "index_id" in indexData or indexData["index_id"] == "":
        abort(400, {"message": "parameter is a required"})

    if current_user is not None:
        indexData["user_id"] = current_user.id
    else:
        abort(400, {"message": "Login required"})

    try:
        index = IndexUserCommunityTag.countdownCommunityTag(indexData)
        if index != False:
            index_schema = IndexSchema(many=True)
            index_list = index_schema.dump(index)
        else:
            abort(400, {"message": "count failed"})
    except ValueError:
        abort(400, {"message": "count failed"})

    return make_response(
        jsonify({"code": 201, "indices": merge_indices_categorytags(index_list)})
    )


##見出しのリストとカテゴリータグリストをマージする
def merge_indices_categorytags(indices_list):

    indices_categorytag_list = []
    categorytag_schema = IndexCategorytagSchema(many=True)

    for indices_dict in indices_list:
        categorytags = IndexCategoryTag.getCategoryTagList(indices_dict)
        categorytags_list = categorytag_schema.dump(categorytags)
        indices_dict["category_tags"] = []
        for categorytags_dict in categorytags_list:
            if indices_dict["id"] == categorytags_dict["index_id"]:
                indices_dict["category_tags"].append(
                    {
                        "id": categorytags_dict["category_tag_id"],
                        "category_tag_name": categorytags_dict["category_name"],
                    }
                )
        indices_categorytag_list.append(indices_dict)

    return indices_categorytag_list
