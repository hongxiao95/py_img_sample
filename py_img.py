#coding:utf-8

from threading import Thread
from tkinter import *
from tkinter.ttk import *
from tkinter.filedialog import askopenfilename
from tkinter import messagebox
import os
from io import BytesIO
from PIL import Image, ImageTk
import time

from utilpkg.Calcer import CODE_PROT_SINGLE_CLR, DATA_PROT_BYTES, DATA_PROT_V_1, Calcer


app_version = "1.0 Beta"
# 最大50M
MAX_FILE_SIZE = 1024 * 1024 * 50
CANVAS_SIDE_SIZE = 450
CANVAS_SIDE_PADDING_RATE = 1.03
CANVAS_COL = 3

IMAGE_BUFFER_SIZE = 6
USING_VERSION = 22


AUTHOR_DESC = f"版本: {app_version} "

class ImgTestUI():
    def __init__(self):
        self.main_win = Tk()
        self.main_win.wm_title("图像测试")
        self.pure_file_name = ""
        self.img_tk_buffer = [0 for i in range(IMAGE_BUFFER_SIZE)]
        self.img_handles = [0 for i in range(IMAGE_BUFFER_SIZE)]
        self.buffer_index = 0

        self.source_file = None
        self.source_bio = BytesIO()
        self.transfer = None

        self.is_pause = False
        self.call_stop = False
        self.is_stoped = False
        self.rec_thread = None

        self._prepare_components()
        self.reset_app()        

    def run(self):
        self.main_win.mainloop()

    def _prepare_components(self):

        self.chosen_file_name_var = StringVar()
        self.choose_file_entry = Entry(self.main_win, state="readonly", textvariable=self.chosen_file_name_var)
        self.choose_file_btn = Button(self.main_win, text = "请选择文件", command=self.ask_file)
        self.choose_file_entry.grid(column=0, row=0, columnspan=6, sticky=EW)
        self.choose_file_btn.grid(column=6, row=0, columnspan=2, sticky=EW)

        self.qr_canvas = Canvas(self.main_win, width=int(CANVAS_SIDE_SIZE * CANVAS_SIDE_PADDING_RATE * CANVAS_COL), height=CANVAS_SIDE_SIZE, background="white")
        self.qr_canvas.grid(column=0, row=1, columnspan=8, rowspan=8)

        self.speed_var = DoubleVar()
        self.speed_var.set(5)

        self.speed_var_int = IntVar()
        self.speed_var_int.set(5)

        self.speed_label = Label(self.main_win, text="速率调节")
        self.speed_scale = Scale(self.main_win, from_=1, to=15, variable=self.speed_var, \
            command=lambda x: self.speed_var_int.set(int(float(x))))
        self.speed_value_label = Label(self.main_win, textvariable=self.speed_var_int)

        self.speed_label.grid(column=0, row=9, sticky=EW)
        self.speed_scale.grid(column=1, row=9, columnspan=6, sticky=EW)
        self.speed_value_label.grid(column=7, row=9, sticky=E)

        # 开始/继续 暂停 停止（归零）
        self.start_btn_var = StringVar()
        self.start_btn_var.set("开始")
        self.start_btn = Button(self.main_win, textvariable=self.start_btn_var, command=self.on_start_btn)
        self.pause_btn = Button(self.main_win, text="暂停", command=self.on_pause_btn)
        self.stop_btn = Button(self.main_win, text="停止", command=self.on_stop_btn)
        self.start_btn.grid(column=0, row=10, columnspan=4, sticky=EW)
        self.pause_btn.grid(column=4, row=10, columnspan=2, sticky=EW)
        self.stop_btn.grid(column=6, row=10, columnspan=2, sticky=EW)

        # 补帧
        self.patch_frame_checkbtn_var = BooleanVar()
        self.patch_frame_checkbtn_var.set(False)
        self.patch_frame_checkbtn = Checkbutton(self.main_win, onvalue=True, offvalue=False, text="补帧", variable=self.patch_frame_checkbtn_var)
        
        self.patch_frames_var = StringVar()
        self.patch_frames_var.set("")
        self.patch_entry = Entry(self.main_win, textvariable=self.patch_frames_var)

        self.patch_frame_checkbtn.grid(column=0, row=11, sticky=EW)
        self.patch_entry.grid(column=1, row=11, columnspan=7, sticky=EW)

        # 上一帧 下一帧
        self.prev_frame_btn = Button(self.main_win, text="上一帧")
        self.next_frame_btn = Button(self.main_win, text="下一帧")

        self.prev_frame_btn.grid(column=0, row=12, columnspan=1, sticky=EW)
        self.next_frame_btn.grid(column=1, row=12, columnspan=3, sticky=EW)

        # 跳转到某帧
        self.skip_spin_box = Spinbox(self.main_win, from_=0, to=1000, value=0, increment=1, validate="focus", validatecommand=self._check_skip_frame_spinbox, width=10)
        self.skip_prev_lable = Label(self.main_win, text="跳到")
        self.skip_after_label = Label(self.main_win, text="帧")
        self.skip_go_btn = Button(self.main_win, text="Go")

        self.skip_prev_lable.grid(column=4, row=12, sticky=EW)
        self.skip_spin_box.grid(column=5, row=12)
        self.skip_after_label.grid(column=6, row=12, sticky=EW)
        self.skip_go_btn.grid(column=7, row=12, sticky=EW)

        # 执行信息
        self.file_size_var = StringVar()
        self._set_file_size_tip(is_reset=True)
        self.file_size_label = Label(self.main_win, textvariable=self.file_size_var)

        self.file_speed_var = StringVar()
        self._set_file_speed_tip(is_reset=True)
        self.file_speed_label = Label(self.main_win, textvariable=self.file_speed_var)

        self.cur_tips = StringVar()
        self.reset_tip()
        self.cur_frame_label = Label(self.main_win, textvariable=self.cur_tips)

        self.file_size_label.grid(column=0, row=13, columnspan=2, sticky=W)
        self.file_speed_label.grid(column=2, row=13, columnspan=3, sticky=W)
        self.cur_frame_label.grid(column=5, row=13, columnspan=3, sticky=E)


        # 进度条
        self.progress_var = IntVar()
        self.progress_var.set(0)
        self.progress_bar = Progressbar(self.main_win, maximum=100, variable=self.progress_var, mode="determinate")
        self.progress_bar.grid(column=0, row=14, columnspan=8, sticky=EW)


        # 作者信息
        self.author_info_label = Label(self.main_win, text=AUTHOR_DESC, foreground="gray")
        self.author_info_label.grid(column=0, row=15, columnspan=8, sticky=E)


        return

    def reset_app(self):
        '''
        重置整个应用，清除当前选择的文件和缓存
        '''
        self.source_file = None
        self.source_bio = BytesIO()
        self.transfer = None
        self.pure_file_name = ""
        self.reset_tip()
        self.reset_task()

    def reset_task(self):
        
        if (self.transfer is None) == False:
            self.transfer.reset_transfer_state()
            self.update_tip(f"文件初始化完成, Meta帧 / {self.transfer.total_batch_count}帧")



        self.qr_canvas.delete("all")


        self.speed_var.set(5)
        self.speed_var_int.set(5)


        self.skip_spin_box.set(0)

        self.start_btn_var.set("开始")
        self.start_btn.config(state="normal")
        self.pause_btn.config(state="disabled")
        self.stop_btn.config(state="disabled")
        self.prev_frame_btn.config(state="disabled")
        self.next_frame_btn.config(state="disabled")
        self.skip_go_btn.config(state="disabled")


        self.progress_var.set(0)

        self.qr_canvas.delete("all")
        self.img_tk_buffer = [0 for i in range(IMAGE_BUFFER_SIZE)]
        self.img_handles = [0 for i in range(IMAGE_BUFFER_SIZE)]
        self.buffer_index = 0


        self._set_file_speed_tip(is_reset=True)


        self.is_pause = False
        self.call_stop = False
        self.is_stoped = False

        return

    def _set_file_speed_tip(self, file_speed_KB:float = 0, fps:float=0, est_s:float=0, is_reset:bool = False):
        if is_reset:
            self.file_speed_var.set("当前无速度")
            return

        self.file_speed_var.set(f"均速:{file_speed_KB:5.2f}KB/s, fps:{fps:5.2f}, est: {est_s:5.0f} s")

    def _set_file_size_tip(self, file_size_B:int = 0, is_reset = False):
        if is_reset:
            self.file_size_var.set("未选择文件")
            return

        unit = "B"
        file_size = file_size_B
        if file_size > 1024:
            file_size = file_size / 1024
            unit = "KB"
            if file_size > 1024:
                file_size = file_size / 1024
                unit = "MB"
        self.file_size_var.set(f"大小：{file_size:.2f} {unit}")
        return   

    def on_start_btn(self):
        if self.transfer is None:
            messagebox.showerror("无法开始","未选择文件!")
            return


        if self.is_pause is False:
            self.call_stop = False
            self.is_stoped = False
            
            self.transfer_thread = Thread(target=self.run_task, name="run_task_thread", daemon=True)
            self.transfer_thread.start()
            
        else:

            self.is_stoped = False
            self.is_pause = False
        
        self.start_btn.config(state="disabled")
        self.pause_btn.config(state="normal")
        self.stop_btn.config(state="normal")

    def on_pause_btn(self):
        self.is_pause = True
        self.pause_btn.config(state="disabled")
        self.start_btn.config(state="normal")
        self.start_btn_var.set("继续")

    def on_stop_btn(self):
        self.call_stop = True
        self.is_pause = False
        wait_stop_thread = Thread(target=self._wait_for_stop_success, name="wait_stop_thread", daemon=True)
        wait_stop_thread.start()
        

    def _wait_for_stop_success(self):
        while True:
            if self.is_stoped is True:
                break
            time.sleep(0.2)
            
        self.pause_btn.config(state="disabled")
        self.start_btn.config(state="normal")
        self.start_btn_var.set("开始")
        self.reset_task()

    def update_tip(self, tip):
        self.cur_tips.set(tip)

    def reset_tip(self):
        self.cur_tips.set("当前无任务")
        self._set_file_speed_tip(is_reset=True)
        self._set_file_size_tip(is_reset=True)

    def ask_file(self):

        self.reset_app()


        file_name = askopenfilename()
        file_name = file_name.replace("/", os.sep)
        
        # 判断文件大小
        with open(file_name, "rb") as tryfile:
            tryfile.seek(0, 2)
            file_size_b = tryfile.tell()
            if file_size_b > MAX_FILE_SIZE:
                messagebox.showerror("文件过大！",f"文件最大限制为{MAX_FILE_SIZE/1024/1024:.2f}MB， 过大文件可考虑分卷压缩")
                return
            self._set_file_size_tip(file_size_b)
            self.pure_file_name = file_name.split(os.sep)[-1]
            self.chosen_file_name_var.set(file_name)
            self.update_tip("正在初始化文件...")
            tryfile.seek(0,0)

            self.source_file = tryfile
            self.source_bio = BytesIO()
            self.source_bio.write(self.source_file.read())
        
        # 加载到app中
        self.transfer = Calcer(self.pure_file_name, self.source_bio, DATA_PROT_BYTES, DATA_PROT_V_1, CODE_PROT_SINGLE_CLR, qr_version=USING_VERSION)

        self.update_tip(f"文件初始化完成, Meta帧 / {self.transfer.total_batch_count}帧")
    
    def _check_skip_frame_spinbox(self) -> bool:
        return True

    def _im_to_canvas_im(self, pil_im: Image) -> PhotoImage:
        pil_im = pil_im.resize((CANVAS_SIDE_SIZE, CANVAS_SIDE_SIZE))
        tk_im = ImageTk.PhotoImage(image=pil_im)
        return tk_im

    def _draw_im_to_canvas(self, im_tk: PhotoImage, pos:int = 0):
        if self.img_handles[self.buffer_index] != 0:
            self.qr_canvas.delete(self.img_handles[self.buffer_index])
        
        self.img_tk_buffer[self.buffer_index] = im_tk
        handle = self.qr_canvas.create_image(int(pos * CANVAS_SIDE_SIZE * CANVAS_SIDE_PADDING_RATE) ,0, image=im_tk, anchor=NW)
        self.img_handles[self.buffer_index] = handle
        self.buffer_index = (self.buffer_index + 1) % IMAGE_BUFFER_SIZE
        self.main_win.update_idletasks()


    def _check_patchs_legal(self, patchs_str:str, total_frame:int) -> tuple:
        patchs_num = []
        try:
            patchs_num = sorted(set([int(x) for x in list(filter(lambda y:y.strip() != "", patchs_str.split(",")))]))

            if len(patchs_num) == 0:
                return (False, "无有效的补丁帧")
                
            illegal_num = list(filter(lambda x: x < 0 or x >= total_frame, patchs_num))

            if len(illegal_num) > 0:
                return (False, f"以下帧数超过合法帧[0,{total_frame}):{illegal_num}")
            
            return (True, patchs_num)
        except ValueError as e:
            messagebox.showerror("出错",f"解析补丁出错, ValueError:{e}")
            return (False, f"解析补丁出错, ValueError:{e}")

    def run_task(self):

        task_st = time.time()
        handled_frames = 0

        # 处理补丁模式
        if self.patch_frame_checkbtn_var.get() is True:
            check_res = self._check_patchs_legal(self.patch_frames_var.get(), self.transfer.total_batch_count)
            if check_res[0] is True:
                self.transfer.open_patchs(check_res[1])
            else:
                messagebox.showerror("补丁模式错误", check_res[1])
        else:
            self.transfer.close_patchs()


        handshake_im = self.transfer.gen_handshake_qr()
        tk_im = self._im_to_canvas_im(handshake_im)
        self._draw_im_to_canvas(tk_im)
        time.sleep(1)
        has_next = True
        
        st = 0
        im_pos = 0
        while has_next is True:
            if self.call_stop is True:
                self.is_stoped = True
                return
            if self.is_pause is True:
                time.sleep(0.2)
                # print("暂停态")
                continue

            data_im = self.transfer.gen_cur_qr()
            has_next = (self.transfer.next_batch() != False)

            tk_im = self._im_to_canvas_im(data_im)

            if im_pos == 0:
                end  = time.time()

                # 决定帧间隔sleep
                frame_work_time = end - st
                frame_ideal_time = 1 / self.speed_var_int.get()
                time_break = frame_ideal_time - frame_work_time
                if time_break > 0:
                    time.sleep(time_break)    

            self._draw_im_to_canvas(tk_im, im_pos)
            handled_frames += 1

            if im_pos == 0:
                st = time.time()
            im_pos = (im_pos + 1) % CANVAS_COL

            task_time = st - task_st
            total_trans_B = handled_frames * self.transfer.frame_pure_data_size_byte
            real_fps = self.transfer.index / task_time

            est_s = -1 if real_fps == 0 else (self.transfer.total_batch_count - self.transfer.index) / real_fps
            self._set_file_speed_tip(total_trans_B / 1024 / task_time, fps=real_fps, est_s=est_s)
            
            self.progress_var.set(self.transfer.index / self.transfer.total_batch_count * 100)
        
        time.sleep(5)
        self.reset_task()


def main():
    global CANVAS_COL, USING_VERSION
    cols = -1
    user_version = -1
    
    while cols == -1:
        i_cols = input(f"每屏码数(1~3)，默认为{CANVAS_COL}： ")
        if i_cols.strip() == "":
            cols = CANVAS_COL
        elif i_cols.strip() in [str(i) for i in range(1,4)]:
            cols = int(i_cols)
        else:
            print("请输入合法数字！")
            continue
    
    while user_version == -1:
        i_user_version = input(f"数据密度(15~31),越小越慢，越大准确率低，默认为{USING_VERSION}： ")
        if i_user_version.strip() == "":
            user_version = USING_VERSION
        elif i_user_version.strip() in [str(i) for i in range(15,32)]:
            user_version = int(i_user_version)
        else:
            print("请输入合法数字！")
            continue

    CANVAS_COL = cols
    USING_VERSION = user_version

    ui = ImgTestUI()
    ui.run()

if __name__ == "__main__":
    main()