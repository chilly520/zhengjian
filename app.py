import streamlit as st
from PIL import Image
from rembg import remove
import io

# 设置网页标题与布局
st.set_page_config(page_title="25级英语考级高清工具", layout="centered")

st.title("📸 高清版·证件照自动生成器")
st.markdown("---")

st.sidebar.header("⚙️ 当前规格：高清模式")
st.sidebar.info("""
- **像素**：960 x 1280
- **DPI**：300
- **目标体积**：500KB - 1MB (最高质量优先)
- **背景**：标准证件蓝
""")

uploaded_file = st.file_uploader("上传原始照片", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    with st.status("正在进行高清重采样与压缩优化...", expanded=True) as status:
        # 1. 加载图片
        input_image = Image.open(uploaded_file)
        
        # 2. AI 抠图
        st.write("正在精准抠像...")
        no_bg_image = remove(input_image)
        
        # 3. 创建 960x1280 画布
        target_w, target_h = 960, 1280
        blue_bg = (67, 142, 219)
        canvas = Image.new("RGB", (target_w, target_h), blue_bg)
        
        # 4. 优化后的构图算法
        st.write("校准构图比例...")
        orig_w, orig_h = no_bg_image.size
        aspect = orig_w / orig_h
        
        top_gap = int(target_h * 0.1) # 顶部1/10留空
        t_person_h = target_h - top_gap
        t_person_w = int(t_person_h * aspect)
        
        if t_person_w < target_w:
            t_person_w = target_w
            t_person_h = int(t_person_w / aspect)
            
        resized_person = no_bg_image.resize((t_person_w, t_person_h), Image.Resampling.LANCZOS)
        
        # 底部对齐粘贴
        paste_x = (target_w - t_person_w) // 2
        paste_y = target_h - t_person_h 
        canvas.paste(resized_person, (paste_x, paste_y), resized_person)
        
        # 5. 修复后的体积控制逻辑
        st.write("优化清晰度与文件体积...")
        # 从质量 100 开始向下探测，确保在不超过 1024KB 的前提下质量最高
        quality = 100
        final_buffer = io.BytesIO()
        
        while quality > 10:
            temp_buffer = io.BytesIO()
            # 锁定 300 DPI
            canvas.save(temp_buffer, format="JPEG", quality=quality, dpi=(300, 300))
            current_size = temp_buffer.tell()
            
            # 只要小于 1000KB (留点余量)，我们就取这个质量
            if current_size <= 1000 * 1024:
                final_buffer = temp_buffer
                # 如果当前质量已经很优秀（比如95以上），且体积超过400KB，直接停止
                if quality >= 95 and current_size >= 400 * 1024:
                    break
                # 如果到了质量 100 体积还没到 400KB (纯色太多的缘故)，也直接停止，因为不能再高了
                if quality == 100:
                    break
                break
            quality -= 2
            
        status.update(label="高清处理完成！", state="complete", expanded=False)

    # 显示
    st.image(canvas, caption="960x1280 高清预览", use_container_width=True)

    # 下载
    st.download_button(
        label="📥 下载高清证件照 (JPG)",
        data=final_buffer.getvalue(),
        file_name="CET_HD_Final.jpg",
        mime="image/jpeg"
    )
    
    st.success(f"✅ 处理成功！\n- 像素: 960x1280\n- 体积: {final_buffer.tell()//1024} KB\n- 分辨率: 300 DPI")
