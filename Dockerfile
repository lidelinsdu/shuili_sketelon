
FROM python:3.9 as builder
WORKDIR /app
COPY ../requirements.txt .
RUN pip install -r requirements.txt PyInstaller -i https://pypi.tuna.tsinghua.edu.cn/simple
COPY ../model5/whls/GDAL-3.4.1-cp39-cp39-manylinux_2_5_x86_64.manylinux1_x86_64.whl .
RUN pip install GDAL-3.4.1-cp39-cp39-manylinux_2_5_x86_64.manylinux1_x86_64.whl -i https://pypi.tuna.tsinghua.edu.cn/simple
COPY .. .
# 在构建阶段，找到 GDAL 数据目录并复制到项目中
RUN mkdir -p /app/gdal_data
RUN cp -r $(python -c "import rasterio; print(rasterio.__path__[0])")/gdal_data/* /app/gdal_data/ || true

# 然后在 PyInstaller 中添加：
# --add-data "/app/gdal_data:gdal"

RUN python -m PyInstaller \
    --onefile \
    --name=fastapi-app \
    --hidden-import=rasterio \
    --hidden-import=rasterio.crs \
    --hidden-import=rasterio.warp \
    --hidden-import=rasterio.transform \
    --hidden-import=rasterio.io \
    --hidden-import=rasterio.sample \
    --hidden-import=rasterio.vrt \
    --hidden-import=rasterio._base \
    --hidden-import=rasterio._env \
    --hidden-import=rasterio._shim \
    --hidden-import=rasterio._features \
    --collect-data=rasterio \
    --collect-data=pyproj \
    --add-data "config:config" \
    --add-data "/app/gdal_data:gdal" \
    main.py


FROM python:3.9-slim

# 创建非 root 用户
RUN useradd --create-home --shell /bin/bash appuser
USER appuser
WORKDIR /home/appuser

COPY --from=builder /app/dist/fastapi-app ./fastapi-app

EXPOSE 8081
CMD ["./fastapi-app"]
