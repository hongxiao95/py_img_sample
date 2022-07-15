#coding:utf-8

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

RECOMMAND_VERSION = 22

DATA_PROT_V_1 = 1

class Calcer(CalcBase):

    def __init__(self, file_name: str, bio: BytesIO, data_prot:str, data_prot_v: int, code_prot:str, confirm_method: int = ConfirmMethod.NO_CFM, qr_version: int=RECOMMAND_VERSION, ext_meta=None, ext_meta_size:int=0, code_encode:str="base85"):
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
        self.code_encode = code_encode
        if self.code_encode not in ["base85","base64"]:
            self.code_encode = "base85"
        
        if "." in self.file_name:
            self.file_type = self.file_name[::-1].split(".")[0][::-1]
        else:
            self.file_type = ""

        self.main_data_inited = False
        
        
        self.trans_uuid = str(uuid.uuid4()).replace("-","")

        
        self.file_bio.seek(0, 2)
        self.file_size_Byte = self.file_bio.tell()

        
        

        if self.code_encode == "base85":
            total_capcity = int(constants.v_max_data_dict[self.version] / 5 * 4) 
        elif self.code_encode == "base64":
            total_capcity = int(constants.v_max_data_dict[self.version] / 4 * 3) 

        self.frame_pure_data_size_byte = total_capcity - DATA_F_META_SIZE_BYTE - self.ext_meta_size

        self.total_batch_count = int(math.ceil(self.file_size_Byte / self.frame_pure_data_size_byte))

        
        self.file_bio.seek(0)
        self.file_md5 = hashlib.md5(self.file_bio.read()).hexdigest()

        #恢复文件指针
        self.file_bio.seek(0,0)

        
        self.hand_shake_pkg = self._gen_handshake_pkg()

        self.main_data_list = []

        
        self.patch_mode = False
        self.patch_frames = []
        self.patchs_pointer = 0

    def open_patchs(self, patch_frames:list):
        self.patch_mode = True
        self.patch_frames = [int(x) for x in patch_frames]
        self.patchs_pointer = 0
        self.index=self.patch_frames[self.patchs_pointer]

    def close_patchs(self):
        self.patch_mode = False
        self.patch_frames = []
        self.patchs_pointer = 0

    def reset_transfer_state(self):
        

        self.file_bio.seek(0,0)
        self.index = 0
        self.close_patchs()



    def next_batch(self):
        
        if self.patch_mode is False:
            if self.index == self.total_batch_count - 1:
                return False
            else:
                self.index += 1
                return self.index
        
        else:
            if self.patchs_pointer == len(self.patch_frames) - 1:
                return False
            else:
                self.patchs_pointer += 1
                self.index = self.patch_frames[self.patchs_pointer]
                return self.index


    def gen_handshake_qr(self) -> Image:
        json_str = self.hand_shake_pkg.gen_hspkg_json()
        qr = qrcode.QRCode(version=RECOMMAND_VERSION, mask_pattern=constants.DEFAULT_MASK_PATTERN)
        try:
            qr.add_data(json_str)
            qr.best_fit()
            return qr.make_image()
        except Exception as e:
            print(f"生成二维码失败,{e}")
            return None

    def gen_cur_qr(self) -> Image:
        if self.data_prot == DATA_PROT_JSON:
            return self._gen_cur_qr_json()
        elif self.data_prot == DATA_PROT_BYTES:
            return self.gen_cur_qr_in_bytes()
        else:
            return None

    def gen_cur_frame_bytes(self, aimed_index = -1, pure_data = False) -> bytes:

        if aimed_index == -1:
            aimed_index  = self.index
        self.file_bio.seek(aimed_index * self.frame_pure_data_size_byte, 0)
        pure_data_bytes = self.file_bio.read(self.frame_pure_data_size_byte)

        
        if pure_data == True:
            return pure_data_bytes

        main_data_obj = MainDataBytesV1(pure_data_bytes, aimed_index, self.total_batch_count, self.trans_uuid)

        return main_data_obj.get_total_data_bytes()


    def gen_cur_qr_in_bytes(self, target_bytes = 0) -> Image:
        if target_bytes == 0:
            target_bytes = self.gen_cur_frame_bytes()
        qr = qrcode.QRCode(version=self.version, mask_pattern=constants.DEFAULT_MASK_PATTERN, box_size=15, border=6)
        try:
            
            if self.code_encode == "base85":
                qr.add_data(QRData(base64.b85encode(target_bytes), mode=MODE_8BIT_BYTE))
            elif self.code_encode == "base64":
                qr.add_data(QRData(base64.b64encode(target_bytes), mode=MODE_8BIT_BYTE))

            im = qr.make_image()
            return im
        except Exception as e:
            print(f"生成二维码失败,{e}")
            return None

        pass

    def _gen_cur_qr_json(self) -> Image:
        json_str = self._gen_batch_data_json()
        
        qr = qrcode.QRCode(39, mask_pattern=5)
        try:
            qr.add_data(json_str)
            
            qr.version = 39 
            
            im = qr.make_image()
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
        handshake_data = HandshakeDataV1(self.file_name, int(self.file_size_Byte / 1024), self.file_type, self.file_md5, self.total_batch_count, self.data_prot,\
            self.data_prot_v, self.confirm_method)

        hand_shake_pkg = HandshakePkgV1(True, StatusCode.OK, "ok", self.trans_uuid, handshake_data, data_qrcode_version=self.version, data_encode=self.code_encode)

        return hand_shake_pkg


class HandshakeDataV1():
    
    def __init__(self, file_name:str, file_size_kB:int, file_type:str, file_md5:str, total_data_frame_count:int, data_prot:str, data_prot_v:str, confirm_method:int = ConfirmMethod.NO_CFM):
        self.file_name = file_name
        self.file_size_kB = file_size_kB
        self.file_type = file_type
        self.file_md5 = file_md5
        self.data_prot = data_prot
        self.data_prot_v = data_prot_v
        self.confirm_method = confirm_method
        self.total_data_frame_count = total_data_frame_count

class HandshakePkgV1():


    def __init__(self, success:bool, status_code:int, status_msg_12:str, transfer_uuid:str, handshake_data:HandshakeDataV1, data_qrcode_version:int, data_encode:str):
        self.success = success
        self.status_code = status_code
        self.status_msg_12 = status_msg_12
        self.pkg_version = "1.0"
        self.uuid = transfer_uuid
        self.data_qrcode_version = data_qrcode_version
        self.data_encode = data_encode
        self.main_data = handshake_data.__dict__

        self.main_data_md5 = self._gen_hand_shake_main_data_md5()
        self.hand_shake_data_md5 = self._gen_hdsk_md5()
        
        pass

    def gen_hspkg_json(self) -> str:
        return json.dumps(self.__dict__)

    def _verify(self) -> tuple:
        if StringUtil.is_empty(self.main_data_md5):
            return (False, "主数据md5缺失")
        
        if StringUtil.is_empty(self.hand_shake_data_md5):
            return (False, "握手数据md5缺失")

        if StringUtil.is_empty(self.uuid):
            return (False, "UUID缺失")

        return (True, "OK")

    def _gen_hdsk_md5(self) -> str:

        return StringUtil.get_md5_lowerhex(f"{self.pkg_version}_{self.main_data_md5}_{self.uuid}_{str(self.data_qrcode_version)}+{self.data_encode}")

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
    

    def __init__(self, data_bytes:bytes, cur_index:int, total_frame:int, transfer_uuid:str, ext_meta_size:int = 0, ext_meta_bytes:bytes=None):
        self.data_bytes = data_bytes
        self.cur_index = cur_index
        self.total_frame = total_frame
        self.transfer_uuid = transfer_uuid
        self.ext_meta_size = ext_meta_size 
        self.ext_meta_bytes = ext_meta_bytes
        self.total_data = None

        md5_source = self.data_bytes + bytes(str(self.cur_index), encoding="utf-8") + bytes(str(self.total_frame), encoding="utf-8") + bytes(self.transfer_uuid, encoding="utf-8")
        self.data_md5_str = hashlib.md5(md5_source).hexdigest()[8:24]
        
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
