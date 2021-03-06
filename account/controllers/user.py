from django.db import transaction
from django.db.models import Q

from base import errors
from base import controllers as base_ctl
from account.models import UserModel
from account.controllers import role as role_ctl
from utils.onlyone import onlyone


def login(username, password, is_ldap=False):
    '''
    登录
    '''
    base_query = UserModel.objects.filter(username=username)
    if is_ldap:
        base_query = base_query.filter(typ=UserModel.TYP_LDAP)
    obj = base_query.first()
    if not obj:
        raise errors.CommonError('用户名或密码错误')
    if not obj.check_password(password):
        raise errors.CommonError('用户名或密码错误')
    if obj.status == UserModel.ST_FORBIDDEN:
        raise errors.CommonError('用户已被禁止登录')
    data = {
        'token': obj.gen_token(),
    }
    return data


@onlyone.lock(UserModel.model_sign, 'username', 'username', 30)
def create_user(username, password, name=None, phone=None, email=None, operator=None):
    '''
    创建用户
    '''
    user_obj = UserModel.objects.filter(username=username).first()
    if user_obj:
        raise errors.CommonError('用户已存在')
    data = {
        'username': username,
        'name': name,
        'phone': phone,
        'email': email,
    }
    with transaction.atomic():
        user_obj = base_ctl.create_obj(UserModel, data, operator)
        if not password:
            password = '123456'
        user_obj.set_password(password)
    data = user_obj.to_dict()
    return data


@onlyone.lock(UserModel.model_sign, 'obj_id', 'obj_id', 30)
def update_user(obj_id, name=None, password=None, phone=None, email=None, operator=None):
    '''
    编辑用户
    '''
    obj = base_ctl.get_obj(UserModel, obj_id)
    if not obj:
        raise errors.CommonError('用户不存在')
    if is_admin(obj):
        raise errors.CommonError('超级管理员用户不允许编辑')
    data = {
        'name': name,
        'phone': phone,
        'email': email,
    }
    with transaction.atomic():
        user_obj = base_ctl.update_obj(UserModel, obj_id, data, operator)
        if password:
            user_obj.set_password(password)
    data = user_obj.to_dict()
    return data


@onlyone.lock(UserModel.model_sign, 'obj_id', 'obj_id', 30)
def delete_user(obj_id, operator=None):
    '''
    删除用户
    '''
    obj = base_ctl.get_obj(UserModel, obj_id)
    if is_admin(obj):
        raise errors.CommonError('超级管理员用户不允许删除')

    with transaction.atomic():
        base_ctl.delete_obj(UserModel, obj_id, operator)


def is_admin(user_obj):
    '''
    判断用户是否是超级用户
    '''
    if user_obj.typ == UserModel.TYP_NORMAL and user_obj.username == 'admin':
        return True
    return False


def get_users(keyword=None, page_num=None, page_size=None, operator=None):
    '''
    获取用户列表
    '''
    base_query = UserModel.objects
    if keyword:
        base_query = base_query.filter(Q(username__icontains=keyword)|
                                       Q(name__icontains=keyword))
    total = base_query.count()
    objs = base_ctl.query_objs_by_page(base_query, page_num, page_size)
    data_list = [obj.to_dict() for obj in objs]
    data = {
        'total': total,
        'data_list': data_list,
    }
    return data


def get_user(obj_id, operator=None):
    '''
    获取用户信息
    '''
    obj = base_ctl.get_obj(UserModel, obj_id)
    data = obj.to_dict()
    return data


def get_user_info(obj_id, operator=None):
    '''
    获取用户详情信息
    '''
    user_data = get_user(obj_id)
    if user_data.get('username') == 'admin':
        mods = ['mod']
        permissions = ['admin']
    else:
        mod_objs = role_ctl.get_mods_by_user_id(obj_id)
        mods = [obj.sign for obj in mod_objs]
        permission_objs = role_ctl.get_permissions_by_user_id(obj_id)
        permissions = [obj.sign for obj in permission_objs]
    data = {
        'user': user_data,
        'mods': mods,
        'permissions': permissions,
    }
    return data


def has_permission(user_id, permission):
    '''
    判断用户是否有权限
    '''
    obj = base_ctl.get_obj(UserModel, user_id)
    if obj.username == 'admin':
        return True
    permission_objs = role_ctl.get_permissions_by_user_id(user_id)
    permissions = [obj.sign for obj in permission_objs]
    if permission in permissions:
        return True
    return False
