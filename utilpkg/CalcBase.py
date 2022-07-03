#coding:utf-8

class CalcBase():
    
    def __init__(self):
        pass

    def loadConfig(self):
        pass


class ConfigBase():
    '''
    配置基础类，定义了一些配置
    '''
    def __init__(self):
        pass

class StatusCode():
    OK = 0
    def __init__(self):
        pass

class ConfirmMethod():
    '''
    确认方式
    '''
    NO_CFM = 0
    # QR_CFM = 1
    # BEEP_CFM = 2

    def __init__(self):
        pass

class DataProt():
    '''
    主数据协议
    '''
    SINGLE_COLOR = "single-color"
    RGB = "rgb"

    
