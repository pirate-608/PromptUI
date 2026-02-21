cmake_minimum_required(VERSION 3.10)

# ========================================================
# 【关键设置】在 project() 之前定义
# 作用：告诉 CMake 在 MinGW 下生成 DLL 时不要加 "lib" 前缀
# 结果：生成 analyzer.dll 而不是 libanalyzer.dll
# ========================================================
if(MINGW OR MSYS OR CYGWIN)
    set(CMAKE_SHARED_LIBRARY_PREFIX "")
endif()

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

# MinGW 静态链接设置 (避免依赖 libgcc 等 DLL)
if(MINGW)
    target_link_options(analyzer PRIVATE -static)
endif()

set_target_properties(analyzer PROPERTIES
    OUTPUT_NAME "analyzer"
    # 显式指定输出目录为构建目录 (VS Code 默认为 promptui/build)
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}
    LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}
    ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}
)
target_link_libraries(analyzer m)

if(UNIX OR MINGW)
    target_link_libraries(analyzer pthread)
endif()

# 生成 CLI 可执行文件
add_executable(analyzer_cli src/main.c src/list.c)
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
# 2. 复制到项目根目录 (promptui/) -> 供 Python 运行时调用
# ========================================================

# 1. 复制到 build 目录
file(COPY ${CMAKE_CURRENT_SOURCE_DIR}/dict 
    DESTINATION ${CMAKE_BINARY_DIR})

# 2. 复制到项目根目录 (即 c_modules 的上一级)
get_filename_component(PROJECT_ROOT_DIR "${CMAKE_CURRENT_SOURCE_DIR}/.." ABSOLUTE)

file(COPY ${CMAKE_CURRENT_SOURCE_DIR}/dict 
    DESTINATION ${PROJECT_ROOT_DIR})

message(STATUS "✅ Dictionaries deployed to: ${PROJECT_ROOT_DIR}/dict")