# Python 코딩 스타일

Python 코드는 `D:\workspace\excavator_end_point_control`의 스타일을 따른다.
판단이 애매하면 `utils/warning_target.py`(함수), `utils/can_msg_parser.py`(클래스)를 읽고 맞춘다.
아래 규칙은 python-expert 에이전트의 기본 규칙(줄 길이 88, `UPPER_SNAKE_CASE` 상수, 이름의 단위 접미사 등)보다 우선한다.

## 포맷

- 줄 길이는 120자까지 허용한다.
- 문자열은 작은따옴표(`'`)를 기본으로 쓴다.
- 줄바꿈한 인자는 hanging indent가 아니라 여는 괄호 위치에 맞춰 정렬한다.
- 함수와 클래스 사이는 빈 줄 2개, `return` 앞에는 빈 줄 1개를 둔다. 한 줄짜리 함수는 예외다.
- `if`/`else` 블록이 길면 분기 사이에 빈 줄을 넣어 구분한다.
- `ruff format`과 Black은 실행하지 않는다. 따옴표와 정렬을 이 규칙과 다르게 바꾼다.

```python
est_depth = est_pipe_depth_euclidean(target_position=bucket_global_pos, pipe_position=pipe_coords_tm_interp,
                                     pipe_depth=np.negative(pipe_depth_interp))
```

## import

- 표준 라이브러리 → 서드파티 → 로컬(`utils.*`) 순으로 쓰고, 그룹 사이에 빈 줄을 넣지 않는다.
- 간단한 표준 라이브러리 모듈은 한 줄에 묶어도 된다: `import time, threading, argparse`
- `numpy`는 `np`, `pandas`는 `pd`로 import한다.
- import 블록 뒤에는 빈 줄 2개를 둔다.

## 이름

- 함수와 변수는 `snake_case`, 클래스는 `PascalCase`를 쓴다.
- 함수 이름은 동작 접두사로 시작한다: `get_`, `read_`, `create_..._msg`, `est_`(추정), `calculate_`, `interp_`, `convert_`
- 이름은 대상과 속성이 드러나게 길게 쓴다: `bucket_global_pos`, `pipe_safety_boundary_coords_tm`
- 도메인에서 자주 쓰는 축약은 허용한다: `pos`, `est`, `coord`, `interp`, `msg`, `arr`
- 시간 관계는 접미사로 나타낸다: 현재 값 `_t0`, 이전 값 `_t1` 또는 `_prv`
- 모듈 수준 설정값도 소문자 `snake_case`로 쓰고, 단위는 이름이 아니라 주석에 적는다: `boom_length = 4400  # unit: mm`
- 클래스 내부 속성과 내부 메서드는 `__` 접두사를 쓴다: `self.__buffer`, `def __time_elapsed(self)`

## 타입 힌트

- `np.ndarray`, `float`, `int`, `str` 인자와 반환값에 힌트를 단다. 자명한 값은 생략해도 된다.
- 바뀌면 안 되는 값은 `typing.Final`로 표시한다: `self.__t0: Final[float] = time.time()`
- 주요 스칼라 상태값은 변수에도 힌트를 단다: `elapsed_time: float = 0.0`

## docstring

참고 프로젝트에는 docstring이 없지만, 이 프로젝트에서는 다음과 같이 쓴다.

- 공개 모듈, 클래스, 함수에 영어 Google 스타일 docstring을 단다: 한 줄 요약, 필요에 따라 `Args:`, `Returns:`, `Raises:`
- 이름만으로 충분히 설명되는 사소한 내부 함수는 생략해도 된다.
- 물리량의 단위와 배열 구조는 docstring에도 적는다.

```python
def get_distance(origin: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Calculate the euclidean distance from an origin to each target position.

    Args:
        origin: Origin position, shape (2,). Unit: meter.
        target: Target positions, shape (n, 2). Unit: meter.

    Returns:
        Distance to each target, shape (n,). Unit: meter.
    """
```

## 주석

- 코드 주석은 영어 소문자로 시작하고 마침표를 찍지 않는다.
- 처리 단계마다 위에 한 줄 주석을 단다: `# calculate relative angle`
- 단위, 배열 구조, 각 요소의 의미는 줄 끝 주석으로 적는다.

```python
excavator_pos = np.zeros(shape=3, dtype=np.float64)  # latitude, longitude, heading
safety_length: float = 0.5  # unit: meter
```

## 관용구

- 호출할 때 키워드 인자를 적극적으로 쓴다: `get_target_boundary(pipe_coords_tm, radius=safety_length_arr, step=10)`
- 배열은 `shape`와 `dtype`을 명시해 미리 할당한다: `np.zeros(shape=3, dtype=np.float64)`
- 수치 계산은 `numpy`로 하고, 각도 변환은 `np.deg2rad`와 `np.rad2deg`를 쓴다.
- 컴프리헨션 대신 `for` 루프를 쓰고, 배열은 `enumerate`로 채운다.
- 식 안의 연산자 공백은 가독성에 맞춰 줄여도 된다: `target_pos[i+1, 0]`, `radius=pipe_diameter/2`
- 문자열 포맷은 f-string을 쓴다.

## 따라 하지 않는 것

참고 프로젝트에 있지만 스타일이 아니라 결함이나 위험 요인이므로 따르지 않는다.

- `global`로 모듈 변수를 바꾸는 함수: 상태가 필요하면 클래스로 묶는다.
- 모듈 최상위에서 실행되는 로직: 진입점은 `main()`과 `if __name__ == '__main__':`로 분리한다.
- `from x import *`
- 객체를 생성해서 기본 인자로 쓰는 것: `packet=can.Message()` (정의 시점에 한 번만 만들어져 모든 호출이 공유한다)
- 주석 처리한 코드, 사용하지 않는 변수와 import
- 문자열 인자로 분기하는 getter: `read_variable('cd_query')`
