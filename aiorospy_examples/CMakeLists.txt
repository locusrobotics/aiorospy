cmake_minimum_required(VERSION 2.8.3)
project(aiorospy_examples)

find_package(catkin REQUIRED COMPONENTS
  catkin_virtualenv
)

catkin_package()

catkin_generate_virtualenv(
  PYTHON_VERSION 3.7
)

set(python_scripts
  scripts/actions
  scripts/aiorospy_telephone
  scripts/services
  scripts/topics
)

catkin_install_python(
  PROGRAMS ${python_scripts}
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

if(CATKIN_ENABLE_TESTING)
  find_package(catkin REQUIRED COMPONENTS roslint)
  roslint_python(${python_scripts})
  roslint_add_test()
endif()
