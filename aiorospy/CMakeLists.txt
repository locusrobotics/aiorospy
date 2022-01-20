cmake_minimum_required(VERSION 3.0.2)
project(aiorospy)

find_package(catkin REQUIRED COMPONENTS
  rospy
)

catkin_package()

catkin_python_setup()

install(FILES requirements.txt
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION})

if(CATKIN_ENABLE_TESTING)
  find_package(catkin REQUIRED COMPONENTS catkin_virtualenv roslint rostest)

  catkin_generate_virtualenv(
    INPUT_REQUIREMENTS requirements.in
    PYTHON_INTERPRETER python3
  )
  set(python_test_scripts
    tests/test_action_client.py
    tests/test_action_server.py
    tests/test_service_proxy.py
    tests/test_service.py
    tests/test_subscriber.py
  )

  roslint_python()
  roslint_python(${python_test_scripts})
  roslint_add_test()

  catkin_install_python(PROGRAMS ${python_test_scripts}
    DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION})

  add_rostest(tests/test_aiorospy.test
    DEPENDENCIES ${PROJECT_NAME}_generate_virtualenv
  )
endif()
