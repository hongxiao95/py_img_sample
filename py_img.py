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
CANVAS_SIDE_SIZE = 400

AUTHOR_DESC = f"版本: {app_version}"

class QrAnyTransUI():
    def __init__(self):
        self.main_win = Tk()
        self.main_win.wm_title("界面测试")
        self.pure_file_name = ""
        self.img_tk_buffer = [0,0]
        self.img_handles = [0,0]
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
        # 选择文件按钮
        self.chosen_file_name_var = StringVar()
        self.choose_file_entry = Entry(self.main_win, state="readonly", textvariable=self.chosen_file_name_var)
        self.choose_file_btn = Button(self.main_win, text = "请选择文件", command=self.ask_file)
        self.choose_file_entry.grid(column=0, row=0, columnspan=6, sticky=EW)
        self.choose_file_btn.grid(column=6, row=0, columnspan=2, sticky=EW)

        self.qr_canvas = Canvas(self.main_win, width=CANVAS_SIDE_SIZE, height=CANVAS_SIDE_SIZE, background="white")
        self.qr_canvas.grid(column=0, row=1, columnspan=8, rowspan=8)

        # 速度调节 
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

        self.start_btn_var = StringVar()
        self.start_btn_var.set("开始")
        self.start_btn = Button(self.main_win, textvariable=self.start_btn_var, command=self.on_start_btn)
        self.pause_btn = Button(self.main_win, text="暂停", command=self.on_pause_btn)
        self.stop_btn = Button(self.main_win, text="停止", command=self.on_stop_btn)
        self.start_btn.grid(column=0, row=10, columnspan=4, sticky=EW)
        self.pause_btn.grid(column=4, row=10, columnspan=2, sticky=EW)
        self.stop_btn.grid(column=6, row=10, columnspan=2, sticky=EW)

        # 上一帧 下一帧
        self.prev_frame_btn = Button(self.main_win, text="上一帧")
        self.next_frame_btn = Button(self.main_win, text="下一帧")

        self.prev_frame_btn.grid(column=0, row=11, columnspan=2, sticky=EW)
        self.next_frame_btn.grid(column=2, row=11, columnspan=2, sticky=EW)

        # 跳转到某帧
        self.skip_spin_box = Spinbox(self.main_win, from_=0, to=1000, value=0, increment=1, validate="focus", validatecommand=self._check_skip_frame_spinbox, width=10)
        self.skip_prev_lable = Label(self.main_win, text="跳到")
        self.skip_after_label = Label(self.main_win, text="帧")
        self.skip_go_btn = Button(self.main_win, text="Go")

        self.skip_prev_lable.grid(column=4, row=11, sticky=EW)
        self.skip_spin_box.grid(column=5, row=11)
        self.skip_after_label.grid(column=6, row=11, sticky=EW)
        self.skip_go_btn.grid(column=7, row=11, sticky=EW)

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

        self.file_size_label.grid(column=0, row=12, columnspan=2, sticky=W)
        self.file_speed_label.grid(column=2, row=12, columnspan=3, sticky=W)
        self.cur_frame_label.grid(column=5, row=12, columnspan=3, sticky=E)


        # 进度条
        self.progress_var = IntVar()
        self.progress_var.set(0)
        self.progress_bar = Progressbar(self.main_win, maximum=100, variable=self.progress_var, mode="determinate")
        self.progress_bar.grid(column=0, row=13, columnspan=8, sticky=EW)


        # 作者信息
        self.author_info_label = Label(self.main_win, text=AUTHOR_DESC, foreground="gray")
        self.author_info_label.grid(column=0, row=14, columnspan=8, sticky=E)


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
        
        # 
        if (self.transfer is None) == False:
            self.transfer.reset_transfer_state()
            self.update_tip(f"文件初始化完成, Meta帧 / {self.transfer.total_batch_count}帧")


        # 
        self.qr_canvas.delete("all")

        # 
        self.speed_var.set(5)
        self.speed_var_int.set(5)

        # 
        self.skip_spin_box.set(0)

        # 
        self.start_btn_var.set("开始")
        self.start_btn.config(state="normal")
        self.pause_btn.config(state="disabled")
        self.stop_btn.config(state="disabled")
        self.prev_frame_btn.config(state="disabled")
        self.next_frame_btn.config(state="disabled")
        self.skip_go_btn.config(state="disabled")

        # 
        self.progress_var.set(0)

        self.qr_canvas.delete("all")
        self.img_tk_buffer = [0,0]
        self.img_handles = [0,0]
        self.buffer_index = 0

        # 
        self._set_file_speed_tip(is_reset=True)

        # 
        self.is_pause = False
        self.call_stop = False
        self.is_stoped = False

        return

    def _set_file_speed_tip(self, file_speed_KB:float = 0, is_reset:bool = False):
        if is_reset:
            self.file_speed_var.set("当前无速度")
            return

        self.file_speed_var.set(f"均速:{file_speed_KB:.2f}KB")

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

        # 
        if self.is_pause is False:
            self.call_stop = False
            self.is_stoped = False
            
            self.transfer_thread = Thread(target=self.run_task, name="run_task_thread", daemon=True)
            self.transfer_thread.start()
            
        else:
            # 
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
        # 扔到另外的线程做停止完成的后续工作
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

        # 
        self.reset_app()

        # 
        file_name = askopenfilename()
        file_name = file_name.replace("/", os.sep)
        
        # 
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
        
        # 
        self.transfer = Calcer(self.pure_file_name, self.source_bio, DATA_PROT_BYTES, DATA_PROT_V_1, CODE_PROT_SINGLE_CLR)

        self.update_tip(f"文件初始化完成, Meta帧 / {self.transfer.total_batch_count}帧")
    
    def _check_skip_frame_spinbox(self) -> bool:
        return True

    def _im_to_canvas_im(self, pil_im: Image) -> PhotoImage:
        pil_im = pil_im.resize((CANVAS_SIDE_SIZE, CANVAS_SIDE_SIZE))
        tk_im = ImageTk.PhotoImage(image=pil_im)
        return tk_im

    def _draw_im_to_canvas(self, im_tk: PhotoImage):
        if self.img_handles[self.buffer_index] != 0:
            self.qr_canvas.delete(self.img_handles[self.buffer_index])
        
        self.img_tk_buffer[self.buffer_index] = im_tk
        handle = self.qr_canvas.create_image(0,0, image=im_tk, anchor=NW)
        self.img_handles[self.buffer_index] = handle
        self.buffer_index = 1 - self.buffer_index
        self.main_win.update_idletasks()

    def run_task(self):

        task_st = time.time()
        handled_frames = 0

        handshake_im = self.transfer.gen_handshake_qr()
        tk_im = self._im_to_canvas_im(handshake_im)
        self._draw_im_to_canvas(tk_im)
        time.sleep(1)
        has_next = True
        
        st = 0
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

            # 
            end  = time.time()

            # 
            frame_work_time = end - st
            frame_ideal_time = 1 / self.speed_var_int.get()
            time_break = frame_ideal_time - frame_work_time
            if time_break > 0:
                time.sleep(time_break)    

            # 
            self._draw_im_to_canvas(tk_im)
            handled_frames += 1
            st = time.time()

            # 
            task_time = st - task_st
            total_trans_B = handled_frames * self.transfer.frame_pure_data_size_byte
            self._set_file_speed_tip(total_trans_B / 1024 / task_time)

            
            # 
            # 
            self.update_tip(f"当前处理 {self.transfer.index}/ {self.transfer.total_batch_count}帧")
            
            self.progress_var.set(self.transfer.index / self.transfer.total_batch_count * 100)
        
        time.sleep(5)
        self.reset_task()

def main():

    ui = QrAnyTransUI()
    ui.run()

if __name__ == "__main__":
    main()