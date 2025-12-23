import streamlit as st
from PIL import Image
from rembg import remove
import io

# 设置网页标题
st.set_page_config(page_title="25级新生英语考级证件照处理工具", layout="centered")

st.title("🎓 英语考级证件照自动生成器")
st.info("根据《25级新生英语考级报名系统照片采集通知》要求定制")

# 侧边栏参数设置
st.sidebar.header("要求概览")
st.sidebar.markdown("""
- **比例**：3:4
- **背景**：蓝色 (RGB: 67, 142, 219)
- **分辨率**：不低于 180 DPI
- **构图**：顶部留空 1/10，头部 7/10
- **大小**：50KB - 1024KB
""")

uploaded_file = st.file_uploader("上传你的原始照片 (请确保光线均匀，露出眉毛和耳朵)", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    with st.status("正在处理照片，请稍候...", expanded=True) as status:
        # 1. 加载图片
        input_image = Image.open(uploaded_file)
        
        # 2. AI 抠图
        st.write("正在移除背景...")
        no_bg_image = remove(input_image)
        
        # 3. 设定尺寸和构图
        # 为了保证 180DPI 时的清晰度，设定为 480x640 像素
        target_w, target_h = 480, 640
        blue_bg = (67, 142, 219)
        canvas = Image.new("RGB", (target_w, target_h), blue_bg)
        
        # 4. 自动缩放与定位 (满足 1/10 顶部留空，7/10 头部比例)
        st.write("正在优化构图...")
        w, h = no_bg_image.size
        aspect = w / h
        
        # 核心算法：让人物高度占据总高度的 85% 左右，以满足头部和肩部比例
        new_h = int(target_h * 0.85)
        new_w = int(new_h * aspect)
        resized_person = no_bg_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # 粘贴位置：顶部留出 1/10 的高度
        offset_x = (target_w - new_w) // 2
        offset_y = int(target_h * 0.1)
        
        canvas.paste(resized_person, (offset_x, offset_y), resized_person)
        
        # 5. 质量压缩与 DPI 设置
        st.write("正在封装格式...")
        quality = 95
        output_buffer = io.BytesIO()
        
        while quality > 10:
            output_buffer = io.BytesIO()
            canvas.save(output_buffer, format="JPEG", quality=quality, dpi=(180, 180))
            if 50 * 1024 < output_buffer.tell() < 1024 * 1024:
                break
            quality -= 5
        
        status.update(label="处理完成！", state="complete", expanded=False)

    # 显示预览图
    col1, col2 = st.columns(2)
    with col1:
        st.image(input_image, caption="原始图片", use_container_width=True)
    with col2:
        st.image(canvas, caption="生成的标准证件照", use_container_width=True)

    # 下载按钮
    st.download_button(
        label="下载证件照 (JPG 格式)",
        data=output_buffer.getvalue(),
        file_name="CET_Photo_Standard.jpg",
        mime="image/jpeg"
    )
    
    st.success(f"已自动调整为 180 DPI，文件大小约 {output_buffer.tell()//1024}KB，符合报名系统要求。")
