cmake_minimum_required(VERSION 3.19)
project(MUSHWrangler LANGUAGES CXX)

find_package(Qt6 REQUIRED COMPONENTS Core Widgets LinguistTools Network Qml)

qt_standard_project_setup()

qt_add_executable(MUSHWrangler
    WIN32 MACOSX_BUNDLE
    main.cpp

    mushwrangler.cpp
    mushwrangler.h
    ansiparser.h ansiparser.cpp
    muclientinstance.h muclientinstance.cpp
    telnetprotocol.h telnetprotocol.cpp
    json.hpp
    config.h config.cpp
    settingsmanager.h settingsmanager.cpp



)

qt_add_translations(
    TARGETS MUSHWrangler
    TS_FILES MUSHWrangler_en_US.ts
)

target_link_libraries(MUSHWrangler
    PRIVATE
        Qt::Core
        Qt::Widgets
        Qt::Network
        Qt::Qml
)

include(GNUInstallDirs)

target_compile_definitions(MUSHWrangler
    PRIVATE HAVE_ZLIB
)

install(TARGETS MUSHWrangler
    BUNDLE  DESTINATION .
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
)

qt_generate_deploy_app_script(
    TARGET MUSHWrangler
    OUTPUT_SCRIPT deploy_script
    NO_UNSUPPORTED_PLATFORM_ERROR
)
install(SCRIPT ${deploy_script})
