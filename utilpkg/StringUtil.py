#coding:utf-8

import hashlib, random

def is_empty(a:str) -> bool:
    '''
    判断字符串是否为None或者空
    '''
    return a is None or a.strip() == ""

def get_md5_lowerhex(content: str) -> bool:
    '''
    生成md5字符串
    '''
    if content == None:
        content = ""

    md5 = hashlib.md5(content.encode("UTF-8"))
    return md5.hexdigest()

def gen_random_bytes(bytes_len: int):
    word_tpl = "qwertyuiop[]asdfghjkl;'zxcvbnm,./=-0987654321"
    res_l = []
    for i in range(bytes_len):
        res_l.append(word_tpl[random.randint(0,len(word_tpl) - 1)])
    return "".join(res_l).encode("utf-8")