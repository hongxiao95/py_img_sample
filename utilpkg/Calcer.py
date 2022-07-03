#coding:utf-8

from curses import meta
from io import BytesIO
from tkinter import Image
from utilpkg.CalcBase import ConfirmMethod, StatusCode, CalcBase
from utilpkg import StringUtil
import hashlib, json, base64, math, uuid
import qrcode
from PIL.Image import Image
from utilpkg import constants
from qrcode.util import QRData, MODE_8BIT_BYTE

CODE_PROT_SINGLE_CLR = "single-color"
CODE_PROT_RGB = "rgb"

DATA_PROT_JSON = "JSON"
DATA_PROT_BYTES = "BYTES"

BATCH_SIZE_BYTE = 1536


DATA_F_META_SIZE_BYTE = 20

MAX_EXT_META_SIZE_BYTE = 63

RECOMMAND_VERSION = 34

DATA_PROT_V_1 = 1

class Calcer(CalcBase):

    
    def __init__(self, file_name: str, bio: BytesIO, data_prot:str, data_prot_v: int, code_prot:str, confirm_method: int = ConfirmMethod.NO_CFM, qr_version: int=RECOMMAND_VERSION, ext_meta=None, ext_meta_size:int=0):
        CalcBase.__init__(self)
        self.file_name = file_name
        self.file_bio = bio
        self.data_prot = data_prot
        self.code_prot = code_prot
        self.confirm_method = confirm_method
        self.index = 0
        self.data_prot_v = data_prot_v
        self.version = qr_version
        if qr_version < 0 or qr_version > 40:
            self.version = RECOMMAND_VERSION

        self.ext_meta = ext_meta
        self.ext_meta_size = ext_meta_size
        if ext_meta_size < 0 or ext_meta_size > MAX_EXT_META_SIZE_BYTE:
            self.ext_meta_size = 0
            self.ext_meta = None
        
        if "." in self.file_name:
            self.file_type = self.file_name[::-1].split(".")[0][::-1]
        else:
            self.file_type = ""

        self.main_data_inited = False
        
        # 生成UUID
        self.trans_uuid = str(uuid.uuid4()).replace("-","")

        self.file_bio.seek(0, 2)
        self.file_size_Byte = self.file_bio.tell()

        total_capcity = constants.v_max_data_dict[self.version]
        self.frame_pure_data_size_byte = total_capcity - DATA_F_META_SIZE_BYTE - self.ext_meta_size

        self.total_batch_count = int(math.ceil(self.file_size_Byte / self.frame_pure_data_size_byte))


        self.file_bio.seek(0)
        self.file_md5 = hashlib.md5(self.file_bio.read()).hexdigest()

        self.file_bio.seek(0,0)

        # 生成握手包
        self.hand_shake_pkg = self._gen_handshake_pkg()

        self.main_data_list = []


    def reset_transfer_state(self):
        self.file_bio.seek(0,0)
        self.index = 0



    def next_batch(self):
        if self.index == self.total_batch_count - 1:
            return False
        else:
            self.index += 1
            return self.index

    def gen_handshake_qr(self) -> Image:
        json_str = self.hand_shake_pkg.gen_hspkg_json()
        qr = qrcode.QRCode(version=RECOMMAND_VERSION, mask_pattern=constants.DEFAULT_MASK_PATTERN)
        try:
            qr.add_data(json_str)
            qr.best_fit()
            return qr.make_image()
        except Exception as e:
            print(f"生成失败,{e}")
            return None

    def gen_cur_qr(self) -> Image:
        if self.data_prot == DATA_PROT_JSON:
            return self._gen_cur_qr_json()
        elif self.data_prot == DATA_PROT_BYTES:
            return self._gen_cur_qr_bytes()
        else:
            return None


    def _gen_cur_qr_bytes(self) -> Image:
        self.file_bio.seek(self.index * self.frame_pure_data_size_byte, 0)
        pure_data_bytes = self.file_bio.read(self.frame_pure_data_size_byte)

        main_data_obj = MainDataBytesV1(pure_data_bytes, self.index, self.total_batch_count, self.trans_uuid)

        qr = qrcode.QRCode(version=self.version, mask_pattern=constants.DEFAULT_MASK_PATTERN)
        try:
            qr.add_data(QRData(main_data_obj.get_total_data_bytes(), mode=MODE_8BIT_BYTE))
            im = qr.make_image()
            return im
        except Exception as e:
            print(f"生成失败,{e}")
            return None

        pass

    def _gen_cur_qr_json(self) -> Image:
        json_str = self._gen_batch_data_json()
        # print(f"生成JSON耗时: {(end-st) * 1000:.2f} 毫秒")

        qr = qrcode.QRCode(39, mask_pattern=5)
        try:
            qr.add_data(json_str)
            # qr.best_fit()
            qr.version = 39 # 1536字节+base64时，39可以cover
            

            # st = time.time()
            im = qr.make_image()
            # end = time.time()
            # print(f"mk qrimg耗时: {(end-st) * 1000:.2f} 毫秒")

            return im
        except Exception as e:
            print(f"生成二维码失败,{e}")
            return None
        
    def _gen_batch_data_json(self):
        
        main_data = self._gen_main_data_json()

        json_str = ""

        try:
            json_str = json.dumps(main_data.__dict__)
        except Exception as e:
            print(e)
        
        return json_str
        

    def _gen_main_data_json(self):
        self.file_bio.seek(self.index * BATCH_SIZE_BYTE, 0)
        part_bytes = self.file_bio.read(BATCH_SIZE_BYTE)
        part_md5 = hashlib.md5(part_bytes).hexdigest()

        data_b64 = base64.b64encode(part_bytes).decode("utf-8")

        main_data = MainDataJSONV1(data_b64, self.index, self.total_batch_count, self.trans_uuid, part_md5)

        return main_data


    def _gen_handshake_pkg(self):
        handshake_data = HandshakeDataV1(self.file_name, int(self.file_size_Byte / 1024), self.file_type, self.file_md5, self.data_prot,\
            self.data_prot_v, self.confirm_method)

        hand_shake_pkg = HandshakePkgV1(True, StatusCode.OK, "ok", self.trans_uuid, handshake_data)

        return hand_shake_pkg



class HandshakeDataV1():
    '''
    握手传输的主数据
    '''
    def __init__(self, file_name:str, file_size_kB:int, file_type:str, file_md5:str, data_prot:str, data_prot_v:str, confirm_method:int = ConfirmMethod.NO_CFM):
        self.file_name = file_name
        self.file_size_kB = file_size_kB
        self.file_type = file_type
        self.file_md5 = file_md5
        self.data_prot = data_prot
        self.data_prot_v = data_prot_v
        self.confirm_method = confirm_method
        
        pass

class HandshakePkgV1():

    '''
    握手数据包
    '''

    def __init__(self, success:bool, status_code:int, status_msg_12:str, transfer_uuid:str, handshake_data:HandshakeDataV1):
        self.success = success
        self.status_code = status_code
        self.status_msg_12 = status_msg_12
        self.pkg_version = "1.0"
        self.uuid = transfer_uuid
        self.main_data = handshake_data.__dict__

        self.main_data_md5 = self._gen_hand_shake_main_data_md5()
        self.hand_shake_data_md5 = self._gen_hdsk_md5()
        
        pass

    def gen_hspkg_json(self) -> str:
        return json.dumps(self.__dict__)

    def _verify(self) -> tuple:
        if StringUtil.is_empty(self.main_data_md5):
            return (False, "主md5缺失")
        
        if StringUtil.is_empty(self.hand_shake_data_md5):
            return (False, "握手md5缺失")

        if StringUtil.is_empty(self.uuid):
            return (False, "UUID缺失")

        return (True, "OK")

    def _gen_hdsk_md5(self) -> str:
        '''
        多端MD5算法必须一致。
        握手包版本号_主数据md5_uuid 算md5
        '''
        return StringUtil.get_md5_lowerhex(f"{self.pkg_version}_{self.main_data_md5}_{self.uuid}")

    def _gen_hand_shake_main_data_md5(self) -> str:

        return "default"

class MainDataJSONV1():

    def __init__(self, data_b64:str, index: int, total: int, uuid: str, md5:str):
        self.data_b64 = data_b64
        self.index = index
        self.total = total
        self.uuid = uuid
        self.md5 = md5

class MainDataBytesV1():
    '''
    二进制格式的数据包
    '''
    def __init__(self, data_bytes:bytes, cur_index:int, total_frame:int, transfer_uuid:str, ext_meta_size:int = 0, ext_meta_bytes:bytes=None):
        self.data_bytes = data_bytes
        self.cur_index = cur_index
        self.total_frame = total_frame
        self.transfer_uuid = transfer_uuid
        self.ext_meta_size = ext_meta_size 
        self.ext_meta_bytes = ext_meta_bytes
        self.total_data = None

        md5_source = self.data_bytes + bytes(str(self.cur_index), encoding="utf-8") + bytes(str(self.total_frame), encoding="utf-8") + bytes(self.transfer_uuid, encoding="utf-8")
        self.data_md5_str = hashlib.md5(md5_source).hexdigest()
        meta_1_num = self.cur_index
        if self.cur_index < self.total_frame - 1:
            meta_1_num = meta_1_num | (1 << 31)
        meta_1_num = meta_1_num | (self.ext_meta_size << 25)

        meta_1_bytes = meta_1_num.to_bytes(4, byteorder="big")
        self.total_data = meta_1_bytes + bytes(self.data_md5_str, encoding="utf-8")
        if isinstance(self.ext_meta_bytes, bytes):
            self.total_data += self.ext_meta_bytes
        self.total_data += self.data_bytes

    def get_total_data_bytes(self):
        return self.total_data
        

def main():
    bio = BytesIO()
    with open("../../this.pdf", "rb") as afile:
        bio.write(afile.read())

    transfer = Calcer("this.pdf", bio, CODE_PROT_SINGLE_CLR, DATA_PROT_V_1)

    print(transfer.total_batch_count)

    

    pass

if __name__ == "__main__":
    main()
    pass
