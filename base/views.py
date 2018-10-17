import re
from django.db.models import Q
from rest_framework import serializers, status, generics
# 使用APIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework.response import Response
import datetime,time,random
# 缓存配置
from django.core.cache import cache
# JWT配置
from .utils import jwt_payload_handler, jwt_encode_handler,google_otp
from .authentication import JWTAuthentication
from .models import *
from .serializers import *
import uuid,os,requests, json


# 登录的view
class LoginInfoSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

class Login(generics.GenericAPIView):
    serializer_class = LoginInfoSerializer
    def post(self,request):
        print(request.data)
        try:
            serializer = self.get_serializer(data=request.data)
            if not serializer.is_valid():
                return Response({"message": str(serializer.errors), "errorCode": 4, "data": {}})
            data = (serializer.data)
            username = data.get('username')
            password = data.get('password')
            if username.find('@') == -1 or username.find('.') == -1:
                phone = username
                email = None
            else:
                email = username
                phone = None
            phone_re = re.compile(r'^1(3[0-9]|4[57]|5[0-35-9]|7[0135678]|8[0-9])\d{8}$', re.IGNORECASE)
            email_re = re.compile(r'^[a-zA-Z0-9_.-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z0-9]{2,6}$', re.IGNORECASE)
            user = object
            if phone:
                if not phone_re.match(phone):
                    return Response({"message": "手机号格式错误>_<", "errorCode": 2, "data": {}})
                user = User.objects.filter(is_delete=False,phone=phone).first()
                if not user:
                    return Response({"message": "用户不存在>_<", "errorCode": 2, "data": {}})
            if email:
                if not email_re.match(email):
                    return Response({"message": "邮箱格式错误>_<", "errorCode": 2, "data": {}})
                user = User.objects.filter(is_delete=False,email=email).first()
                if not user:
                    return Response({"message": "用户不存在>_<", "errorCode": 2, "data": {}})
            if user.password == password:
                payload = jwt_payload_handler(user)
                token = jwt_encode_handler(payload)
                return Response({"message": "登录成功>_<", "errorCode": 0, "data": {'token':token}})
            else:
                return Response({"message": "密码错误>_<", "errorCode": 0, "data": {}})
        except Exception as e:
            print(e)
            return Response({"message": "未知错误>_<", "errorCode": 1, "data": {}})

class UserRegisterSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
    captcha = serializers.CharField()

class Register(generics.GenericAPIView):
    serializer_class = UserRegisterSerializer
    def post(self,request):
        try:
            print(request.data)
            serializer = self.get_serializer(data=request.data)
            if not serializer.is_valid():
                return Response({"message": str(serializer.errors), "errorCode": 4, "data": {}})
            data = (serializer.data)
            username = data.get('username')
            password = data.get('password')
            captcha = data.get('captcha')
            if username.find('@') == -1 or username.find('.') == -1:
                phone = username
                email = None
            else:
                email = username
                phone = None
            phone_re = re.compile(r'^1(3[0-9]|4[57]|5[0-35-9]|7[0135678]|8[0-9])\d{8}$', re.IGNORECASE)
            email_re = re.compile(r'^[a-zA-Z0-9_.-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z0-9]{2,6}$', re.IGNORECASE)
            if phone:
                if not phone_re.match(phone):
                    return Response({"message": "手机号格式错误>_<", "errorCode": 2, "data": {}})
                # 搜索缓存
                # check_captcha = cache.get("drf:captcha:" + phone)
                print(bool(captcha))
                #  or google_otp(captcha)
                if bool(captcha):
                    # or google_otp(captcha)
                    if captcha == '123456':
                        account_check = User.objects.filter(phone=phone, is_delete=False)
                        if account_check:
                            return Response({"message": "用户已经存在>_<", "errorCode": 2})
                        account = User()
                        account.phone = phone
                        # account.password = create_password(password)
                        # 明文密码
                        account.password = password
                        # account.birthday = datetime.date.today()
                        account.name = phone + '手机用户'
                        # account.group_id = 3
                        account.save()
                        return Response({"message": "ok", "errorCode": 0})
                    else:
                        return Response({"message": "验证码错误>_<", "errorCode": 2})
                else:
                    return Response({"message": "验证码已过期>_<", "errorCode": 2})
            if email:
                if not email_re.match(email):
                    return Response({"message": "邮箱格式错误>_<", "errorCode": 2, "data": {}})
                if not captcha:
                    return Response({"message": "验证码已过期>_<", "errorCode": 2})
                if '123456' != captcha:
                    return Response({"message": "验证码错误>_<", "errorCode": 2})
                account_check = User.objects.filter(email=email, is_delete=False)
                if account_check:
                    return Response({"message": "用户已经存在>_<", "errorCode": 2})
                account = User()
                account.email = email
                # account.password = create_password(password)
                # 明文密码
                account.password = password
                account.name = email + '邮箱用户'
                # account.group_id = 3
                account.save()
                return Response({"message": "ok", "errorCode": 0})
        except Exception as e:
            print(e)
            return Response({"message": "未知错误>_<", "errorCode": 1, "data": {}})


class UserInfo(APIView):
    # 加上用户验证 携带正确token时就会有user，否则就是AnonymousUser 就是没有用户的状态
    authentication_classes = (JWTAuthentication,)
    def get(self,request):
        try:
            # print(request.data)
            if not request.auth:
                return Response({"message": "请先登录>_<", "errorCode": 2, "data": {}})
            user = User.objects.filter(id=request.user.id,is_delete=False).first()
            serializer_user_data = UserSerializer(user)
            json_data = {"message": "ok", "errorCode": 0, "data": {}}
            json_data['data'] = serializer_user_data.data
            return Response(json_data)
        except Exception as e:
            print(e)
            return Response({"message": "未知错误>_<", "errorCode": 1, "data": {}})