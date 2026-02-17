cmake_minimum_required(VERSION 3.10)
project(TextAnalyzer C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# 定义宏以导出 DLL 符号 (Windows)
add_definitions(-DANALYZER_EXPORTS)

include_directories(include)

# 源文件列表
set(LIB_SOURCES
    src/analyzer.c
    src/dict.c
    src/list.c
    src/trie.c
    src/utils.c
)

# 生成动态库
add_library(analyzer SHARED ${LIB_SOURCES})

# ========================================================
# 【关键修改 1】针对 MinGW 的静态链接设置
# 这样编译出来的 DLL 不会依赖 libgcc_s_dw2-1.dll 或 libwinpthread-1.dll
# ========================================================
if(MINGW)
    target_link_options(analyzer PRIVATE -static)
endif()

set_target_properties(analyzer PROPERTIES
    OUTPUT_NAME "analyzer"
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}
    LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}
    ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}
)
target_link_libraries(analyzer m)

# ========================================================
# 【关键修改 2】MinGW 也需要链接 pthread
# ========================================================
if(UNIX OR MINGW)
    target_link_libraries(analyzer pthread)
endif()

# 生成 CLI 可执行文件
add_executable(analyzer_cli src/main.c src/list.c)

# CLI 也要静态链接
if(MINGW)
    target_link_options(analyzer_cli PRIVATE -static)
endif()

target_link_libraries(analyzer_cli analyzer)
set_target_properties(analyzer_cli PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}
)

# ========================================================
# 【自动资源部署】
# 1. 复制到构建目录 (build/) -> 供 analyzer_cli.exe 测试用
# 2. 复制到项目根目录 (promptui/) -> 供 Python run.py 运行时调用
# ========================================================

# 1. 复制到 build 目录
file(COPY ${CMAKE_CURRENT_SOURCE_DIR}/dict 
    DESTINATION ${CMAKE_BINARY_DIR})

# 2. 复制到项目根目录 (即 c_modules 的上一级)
# 使用 get_filename_component 获取绝对路径，比简单的 .. 更稳健
get_filename_component(PROJECT_ROOT_DIR "${CMAKE_CURRENT_SOURCE_DIR}/.." ABSOLUTE)

file(COPY ${CMAKE_CURRENT_SOURCE_DIR}/dict 
    DESTINATION ${PROJECT_ROOT_DIR})

message(STATUS "✅ Dictionaries deployed to Build Dir: ${CMAKE_BINARY_DIR}/dict")
message(STATUS "✅ Dictionaries deployed to Project Root: ${PROJECT_ROOT_DIR}/dict")