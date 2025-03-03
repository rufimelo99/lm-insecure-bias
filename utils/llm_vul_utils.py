import os
import subprocess
import time
import json
import re
from xml.etree.ElementTree import parse
from utils.framework_utils import ROOT_PATH

DEBUG = False

LLM_VUL_DIR = os.path.join(ROOT_PATH, "datasets/APR/llm_vul")

SCRIPTS_DIR = os.path.join(LLM_VUL_DIR, "scripts")

info_json = os.path.join(SCRIPTS_DIR, "vul_location.json")

vjbench_json = os.path.join(SCRIPTS_DIR, "VJBench_data.json")

TIMEOUT_COMPILE = 600
TIMEOUT_TEST = 600

VUL4J_DIR = os.path.join(
    LLM_VUL_DIR, "Vul4J_projects"
)  # the folder contains all the Vul4J projects

VJBENCH_DIR = os.path.join(
    LLM_VUL_DIR, "VJBench_projects"
)  # the folder contains all the VJBench projects


vul4j_bug_id_list = [
    1,
    3,
    4,
    5,
    6,
    7,
    8,
    10,
    12,
    18,
    19,
    20,
    22,
    23,
    25,
    26,
    30,
    39,
    40,
    41,
    43,
    44,
    46,
    47,
    50,
    53,
    55,
    57,
    59,
    61,
    64,
    65,
    66,
    73,
    74,
]
vjbench_bug_id_list = list(range(1002, 1010)) + list(range(10010, 10017))


cve_name_to_int = {
    "Jenkins-3": 1006,
    "Jinjava-1": 1007,
    "Jenkins-1": 1004,
    "Quartz-1": 10010,
    "Retrofit-1": 1009,
    "Ratpack-1": 10015,
    "Json-sanitizer-1": 10014,
    "Jenkins-2": 1005,
    "Flow-1": 10011,
    "Pulsar-1": 10016,
    "Netty-1": 1002,
    "BC-Java-1": 10013,
    "Halo-1": 1008,
    "Flow-2": 10012,
    "Netty-2": 1003,
}

cve_int_to_name = {
    1006: "Jenkins-3",
    1007: "Jinjava-1",
    1004: "Jenkins-1",
    10010: "Quartz-1",
    1009: "Retrofit-1",
    10015: "Ratpack-1",
    10014: "Json-sanitizer-1",
    1005: "Jenkins-2",
    10011: "Flow-1",
    10016: "Pulsar-1",
    1002: "Netty-1",
    10013: "BC-Java-1",
    1008: "Halo-1",
    10012: "Flow-2",
    1003: "Netty-2",
}

with open(f"{ROOT_PATH}/config/config.json", "r") as file:
    JAVA8_DIR = json.load(file)["paths"]["JAVA8_PATH"]


def vul4j_compile_java_file(working_directory, cmd):
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_COMPILE,
        )
    except Exception:
        subprocess.run(["pkill", "-f", cmd])
        return False

    compile_result_txt = os.path.join(working_directory, "VUL4J", "compile_result.txt")
    with open(compile_result_txt, "r") as f:
        compile_result = f.read()
    if "1" in compile_result.strip():
        return True
    else:
        return False


def vul4j_test_java_file(working_directory, cmd):
    time_start = time.time()
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=working_directory,
            timeout=TIMEOUT_TEST,
        )
    except Exception:
        subprocess.run(["pkill", "-f", cmd])
        return 2

    time_elapse = time.time() - time_start
    if result.returncode == -9 or time_elapse > TIMEOUT_TEST:
        return 2

    test_result_json = os.path.join(working_directory, "VUL4J", "testing_results.json")
    with open(test_result_json, "r") as f:
        test_result = json.load(f)
    fail_list = test_result["tests"]["failures"]
    num_run = test_result["tests"]["overall_metrics"]["number_running"]
    if len(fail_list) == 0 and num_run > 0:
        return 1
    else:
        return 0


def cve_compile_java_file(working_directory, cmd):

    cmd = f"export JAVA_HOME={JAVA8_DIR} && export PATH=$JAVA_HOME/bin:$PATH && " + cmd

    try:
        result = subprocess.call(
            cmd,
            shell=True,
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            cwd=working_directory,
            timeout=TIMEOUT_COMPILE,
        )

    except Exception:
        subprocess.run(["pkill", "-f", cmd])
        return False

    if result == 0:
        return True
    else:
        return False


def cve_test_java_file(working_directory, cmd):
    time_start = time.time()
    cmd = f"export JAVA_HOME={JAVA8_DIR} && export PATH=$JAVA_HOME/bin:$PATH && " + cmd

    try:
        result = subprocess.call(
            cmd,
            shell=True,
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            cwd=working_directory,
            timeout=TIMEOUT_COMPILE,
        )
    except Exception:
        subprocess.run(["pkill", "-f", cmd])
        return 2

    time_elapse = time.time() - time_start
    if result == -9 or time_elapse > TIMEOUT_TEST:
        return 2

    if result == 0:
        return 1
    else:
        return 0


def extract_correct_method_code(vul_id, trans):
    VUL_FOLDER = os.path.join(LLM_VUL_DIR, "VJBench-trans", vul_id)
    buggy_loc_name = "structure_change_only"
    buggy_file = os.path.join(
        VUL_FOLDER, "{}_code_structure_change_only.java".format(vul_id)
    )
    if trans == "rename_only" or trans == "rename only" or trans == "original":
        buggy_file = os.path.join(VUL_FOLDER, "{}_original_method.java".format(vul_id))
        buggy_loc_name = "original"
    if not os.path.exists(buggy_file):
        print("buggy file does not exist", buggy_file)
        return None, None, False
    bug_location_file = os.path.join(VUL_FOLDER, "buggyline_location.json")
    if not os.path.exists(bug_location_file):
        print("bug locaion file does not exist", bug_location_file)
        return None, None, False
    with open(bug_location_file, "r") as f:
        buggy_line_dict = json.load(f)

    buggy_line_list = buggy_line_dict[buggy_loc_name]
    buggy_line_start = buggy_line_list[0][0]
    if len(buggy_line_list[0]) == 1:
        buggy_line_end = buggy_line_start
    else:
        buggy_line_end = buggy_line_list[0][1]

    with open(buggy_file, "r") as f:
        lines = f.readlines()
    code_before = lines[: buggy_line_start - 1]
    code_after = lines[buggy_line_end:]

    if DEBUG:
        print("bug_location_file", bug_location_file)
        print("buggy_file", buggy_file)
        print("buggy_line_start", buggy_line_start)
        print("buggy_line_end", buggy_line_end)
        print("code before")
        print("".join(code_before))
        print("code after")
        print("".join(code_after))
    return code_before, code_after, True


def translate_code(raw_code, vul_id_int):
    # if vul_id_int is int
    if isinstance(vul_id_int, int):
        vul_id = "VUL4J-{}".format(vul_id_int)
    else:
        vul_id = vul_id_int

    folder = vul_id
    VUL_FOLDER = os.path.join(LLM_VUL_DIR, "VJBench-trans", vul_id)
    rename_dict_path = os.path.join(
        VUL_FOLDER, "{}_identifier_rename_dict.json".format(vul_id)
    )
    with open(rename_dict_path, "r") as f:
        rename_dict = json.load(f)
    variable_rename_dict = rename_dict["variable"]
    method_rename_dict = rename_dict["method"]
    type_rename_dict = rename_dict["class"]

    map_dict = {**variable_rename_dict, **method_rename_dict}
    map_dict = {**map_dict, **type_rename_dict}

    java_separator = re.compile(
        r'(\s+|;|,|\(|\)|\[|\]|\.|:|<|>|=|\+|-|\*|/|&|\||\^|~|%|!|@|#|\$|\?|{|}|"|\'|`|\\)'
    )

    # use value as key and key as value
    map_dict = {v: k for k, v in map_dict.items()}
    # sort the map by the length of the key string in descending order
    map_dict = dict(
        sorted(map_dict.items(), key=lambda item: len(item[0]), reverse=True)
    )
    # delete the space before and after map dict
    map_dict = {k.strip(): v.strip() for k, v in map_dict.items()}

    # if the dict have map_dict["r"] = "z", and there is code arr.size(), then we should not replace z with r. We use java separator to avoid this.
    code_list = java_separator.split(raw_code)
    # print(code_list)
    for i in range(len(code_list)):
        if code_list[i] in map_dict:

            code_list[i] = map_dict[code_list[i]]
    # convert code_list back to string
    raw_code = "".join(code_list)
    # print(raw_code)

    return raw_code


def read_test_results_maven(vul, project_dir):
    surefire_report_files = []
    for r, dirs, files in os.walk(project_dir):
        for file in files:
            filePath = os.path.join(r, file)
            if (
                (
                    "target/surefire-reports" in filePath
                    or "target/failsafe-reports" in filePath
                )
                and file.endswith(".xml")
                and file.startswith("TEST-")
            ):
                surefire_report_files.append(filePath)

    failing_tests_count = 0
    error_tests_count = 0
    passing_tests_count = 0
    skipping_tests_count = 0

    passingTestCases = set()
    skippingTestCases = set()

    failures = []

    for report_file in surefire_report_files:
        with open(report_file, "r") as file:
            xml_tree = parse(file)
            testsuite_class_name = xml_tree.getroot().attrib["name"]
            test_cases = xml_tree.findall("testcase")
            for test_case in test_cases:
                failure_list = {}
                class_name = (
                    test_case.attrib["classname"]
                    if "classname" in test_case.attrib
                    else testsuite_class_name
                )
                method_name = test_case.attrib["name"]
                failure_list["test_class"] = class_name
                failure_list["test_method"] = method_name

                failure = test_case.findall("failure")
                if len(failure) > 0:
                    failing_tests_count += 1
                    failure_list["failure_name"] = failure[0].attrib["type"]
                    if "message" in failure[0].attrib:
                        failure_list["detail"] = failure[0].attrib["message"]
                    failure_list["is_error"] = False
                    failures.append(failure_list)
                else:
                    error = test_case.findall("error")
                    if len(error) > 0:
                        error_tests_count += 1
                        failure_list["failure_name"] = error[0].attrib["type"]
                        if "message" in error[0].attrib:
                            failure_list["detail"] = error[0].attrib["message"]
                        failure_list["is_error"] = True
                        failures.append(failure_list)
                    else:
                        skipTags = test_case.findall("skipped")
                        if len(skipTags) > 0:
                            skipping_tests_count += 1
                            skippingTestCases.add(class_name + "#" + method_name)
                        else:
                            passing_tests_count += 1
                            passingTestCases.add(class_name + "#" + method_name)

    overall_metrics = {
        "number_running": passing_tests_count + error_tests_count + failing_tests_count,
        "number_passing": passing_tests_count,
        "number_error": error_tests_count,
        "number_failing": failing_tests_count,
        "number_skipping": skipping_tests_count,
    }
    tests = {
        "overall_metrics": overall_metrics,
        "failures": failures,
        "passing_tests": list(passingTestCases),
        "skipping_tests": list(skippingTestCases),
    }

    json_data = {"vul_id": vul, "tests": tests}
    return json_data


def read_test_results_gradle(vul, project_dir):
    surefire_report_files = []
    for r, dirs, files in os.walk(project_dir):
        for file in files:
            filePath = os.path.join(r, file)
            if (
                "build/test-results" in filePath
                and file.endswith(".xml")
                and file.startswith("TEST-")
            ):
                surefire_report_files.append(filePath)

    failing_tests_count = 0
    error_tests_count = 0
    passing_tests_count = 0
    skipping_tests_count = 0
    failures = []

    passingTestCases = set()
    skippingTestCases = set()

    for report_file in surefire_report_files:
        with open(report_file, "r") as file:
            xml_tree = parse(file)
            testsuite_class_name = xml_tree.getroot().attrib["name"]
            test_cases = xml_tree.findall("testcase")
            for test_case in test_cases:
                failure_list = {}
                class_name = (
                    test_case.attrib["classname"]
                    if "classname" in test_case.attrib
                    else testsuite_class_name
                )
                method_name = test_case.attrib["name"]
                failure_list["test_class"] = class_name
                failure_list["test_method"] = method_name

                failure = test_case.findall("failure")
                if len(failure) > 0:
                    failing_tests_count += 1
                    failure_list["failure_name"] = failure[0].attrib["type"]
                    if "message" in failure[0].attrib:
                        failure_list["detail"] = failure[0].attrib["message"]
                    failure_list["is_error"] = False
                    failures.append(failure_list)
                else:
                    error = test_case.findall("error")
                    if len(error) > 0:
                        error_tests_count += 1
                        failure_list["failure_name"] = error[0].attrib["type"]
                        if "message" in error[0].attrib:
                            failure_list["detail"] = error[0].attrib["message"]
                        failure_list["is_error"] = True
                        failures.append(failure_list)
                    else:
                        skipTags = test_case.findall("skipped")
                        if len(skipTags) > 0:
                            skipping_tests_count += 1
                            skippingTestCases.add(class_name + "#" + method_name)
                        else:
                            passing_tests_count += 1
                            passingTestCases.add(class_name + "#" + method_name)

    overall_metrics = {
        "number_running": passing_tests_count + error_tests_count + failing_tests_count,
        "number_passing": passing_tests_count,
        "number_error": error_tests_count,
        "number_failing": failing_tests_count,
        "number_skipping": skipping_tests_count,
    }
    tests = {
        "overall_metrics": overall_metrics,
        "failures": failures,
        "passing_tests": list(passingTestCases),
        "skipping_tests": list(skippingTestCases),
    }

    json_data = {"vul_id": vul, "tests": tests}
    return json_data
