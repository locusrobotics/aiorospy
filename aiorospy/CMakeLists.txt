cmake_minimum_required(VERSION 2.8.3)
project(aiorospy)

find_package(catkin REQUIRED COMPONENTS
  rospy
)

catkin_package()

catkin_python_setup()

install(FILES requirements.txt
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION})

if(CATKIN_ENABLE_TESTING)
  find_package(catkin REQUIRED COMPONENTS catkin_virtualenv roslint)

  catkin_generate_virtualenv(
    PYTHON_VERSION 3.7
  )
  roslint_python()
  roslint_add_test()

  catkin_add_nosetests(tests
    DEPENDENCIES ${PROJECT_NAME}_generate_virtualenv
  )
endif()
