cmake_minimum_required(VERSION 2.8.3)
project(aiorospy)

find_package(catkin REQUIRED COMPONENTS
  catkin_virtualenv
  rospy
)

catkin_package()

catkin_generate_virtualenv(
  PYTHON_VERSION 3.6
)

catkin_python_setup()

install(FILES requirements.txt
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION})

catkin_install_python(
  PROGRAMS
        scripts/aiorospy_telephone
        scripts/talker_listener
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

if(CATKIN_ENABLE_TESTING)
  find_package(catkin REQUIRED COMPONENTS roslint)
  roslint_python(${python_scripts})
  roslint_python()
  roslint_add_test()
endif()
