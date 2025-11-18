fn main() {
    // Fix for runng-sys CMake compatibility with CMake 4.x
    // CMake 4.x removed support for projects requiring CMake < 3.5
    if std::env::var("CMAKE_POLICY_VERSION_MINIMUM").is_err() {
        std::env::set_var("CMAKE_POLICY_VERSION_MINIMUM", "3.5");
    }
}

