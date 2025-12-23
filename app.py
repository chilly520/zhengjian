import streamlit as st
from PIL import Image, ImageOps
from rembg import remove, new_session
import io
import gc # 导入垃圾回收

# --- 1. 极低内存配置 ---
st.set_page_config(page_title="证件照工具-稳定版", layout="centered")

# 清理残留内存
gc.collect()

# 使用缓存加载模型，避免重复占用内存
@st.cache_resource
def load_session(model_name):
    return new_session(model_name)

st.title("📸 证件照生成器 (稳定优化版)")

# --- 2. 模式与模型选择 ---
st.sidebar.header("配置选项")
mode = st.sidebar.radio("模式", ("全自动AI", "透明PNG换底", "仅改尺寸"))
model_name = "isnet-general-use"
if mode == "全自动AI":
    m_choice = st.sidebar.selectbox("如果衣服被扣除，请切换模型", ("ISNet (发丝优)", "U2Net (整体稳)"))
    model_name = "isnet-general-use" if "ISNet" in m_choice else "u2net"

# --- 3. 参数锁定 ---
T_W, T_H = 960, 1280
BLUE = (67, 142, 219)

# --- 4. 上传与处理 ---
st.info("提示：若提示资源超出限制，请点击侧边栏最下方的 'Manage app' -> 'Reboot'")
uploaded_file = st.file_uploader("直接拖入图片", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    try:
        with st.status("正在处理...", expanded=True) as status:
            img = Image.open(uploaded_file).convert("RGBA")
            
            # --- 分模式抠图 ---
            if mode == "全自动AI":
                st.write(f"正在加载 {model_name} 模型...")
                sess = load_session(model_name)
                # 内存优化：关闭 alpha_matting 减少计算量，除非必须
                no_bg = remove(img, session=sess)
            elif mode == "透明PNG换底":
                no_bg = img
            else:
                no_bg = None

            # --- 构图 ---
            if no_bg:
                canvas = Image.new("RGB", (T_W, T_H), BLUE)
                w, h = no_bg.size
                scale = (T_H * 0.9) / h
                nw, nh = int(w * scale), int(h * scale)
                if nw < T_W:
                    nw = T_W
                    nh = int(nw * (h/w))
                
                resized = no_bg.resize((nw, nh), Image.Resampling.LANCZOS)
                canvas.paste(resized, ((T_W - nw)//2, T_H - nh), resized)
            else:
                canvas = ImageOps.fit(img.convert("RGB"), (T_W, T_H), Image.Resampling.LANCZOS)

            # --- 压测体积与保存 ---
            st.write("优化体积中...")
            out = io.BytesIO()
            # 采用 95 质量起步，兼顾清晰度与 500KB 目标
            canvas.save(out, format="JPEG", quality=95, dpi=(300, 300))
            
            status.update(label="处理完成！", state="complete")

        st.image(canvas, use_container_width=True)
        st.download_button("📥 下载高清证件照", out.getvalue(), "photo_hd.jpg", "image/jpeg")
        st.success(f"大小: {out.tell()//1024} KB | 300 DPI")

        # --- 5. 强制回收内存 ---
        del img, canvas
        if 'no_bg' in locals(): del no_bg
        gc.collect()

    except Exception as e:
        st.error(f"处理出错，可能是内存不足。请刷新页面重试。报错详情: {e}")
        gc.collect()
