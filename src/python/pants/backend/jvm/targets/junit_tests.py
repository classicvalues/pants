# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).


from pants.backend.jvm.subsystems.junit import JUnit
from pants.backend.jvm.targets.jvm_target import JvmTarget
from pants.backend.jvm.targets.runtime_platform_mixin import RuntimePlatformMixin
from pants.base.deprecated import deprecated, deprecated_conditional
from pants.base.exceptions import TargetDefinitionException
from pants.base.payload import Payload
from pants.base.payload_field import PrimitiveField


class JUnitTests(RuntimePlatformMixin, JvmTarget):
    """JUnit tests.

    :API: public
    """

    java_test_globs = ("*Test.java",)
    scala_test_globs = ("*Test.scala", "*Spec.scala")

    default_sources_globs = java_test_globs + scala_test_globs

    CONCURRENCY_SERIAL = "SERIAL"
    CONCURRENCY_PARALLEL_CLASSES = "PARALLEL_CLASSES"
    CONCURRENCY_PARALLEL_METHODS = "PARALLEL_METHODS"
    CONCURRENCY_PARALLEL_CLASSES_AND_METHODS = "PARALLEL_CLASSES_AND_METHODS"
    VALID_CONCURRENCY_OPTS = [
        CONCURRENCY_SERIAL,
        CONCURRENCY_PARALLEL_CLASSES,
        CONCURRENCY_PARALLEL_METHODS,
        CONCURRENCY_PARALLEL_CLASSES_AND_METHODS,
    ]

    @classmethod
    def subsystems(cls):
        return super().subsystems() + (JUnit,)

    def __init__(
        self,
        cwd=None,
        payload=None,
        timeout=None,
        extra_jvm_options=None,
        extra_env_vars=None,
        concurrency=None,
        threads=None,
        runtime_platform=None,
        **kwargs
    ):
        """
        :param str cwd: working directory (relative to the build root) for the tests under this
          target. If unspecified (None), the working directory will be controlled by junit_run's --cwd
          and --chroot options.
        :param str test_platform: Deprecated. The name of the platform (defined under the jvm-platform subsystem) to
          use for running tests (that is, a key into the --jvm-platform-platforms dictionary). If
          unspecified, the platform will default to the same one used for compilation.
        :param int timeout: A timeout (in seconds) which covers the total runtime of all tests in this
          target. Only applied if `--test-junit-timeouts` is set to True.
        :param list extra_jvm_options: A list of options to be passed to the jvm when running the
          tests. Example: ['-Dexample.property=1', '-DMyFlag', '-Xmx4g'] If unspecified, no extra jvm options will be added.
        :param dict extra_env_vars: A map of environment variables to set when running the tests, e.g.
          { 'FOOBAR': 12 }. Using `None` as the value will cause the variable to be unset.
        :param string concurrency: One of 'SERIAL', 'PARALLEL_CLASSES', 'PARALLEL_METHODS',
          or 'PARALLEL_CLASSES_AND_METHODS'.  Overrides the setting of --test-junit-default-concurrency.
        :param int threads: Use the specified number of threads when running the test. Overrides
          the setting of --test-junit-parallel-threads.
        :param str runtime_platform: The name of the platform (defined under the jvm-platform subsystem)
          to use for runtime (that is, a key into the --jvm-platform-platforms dictionary). If
          unspecified, the platform will default to the first one of these that exist: (1) the
          default_runtime_platform specified for jvm-platform, (2) the platform that would be used for
          the platform kwarg.
        """

        payload = payload or Payload()

        if extra_env_vars is None:
            extra_env_vars = {}
        for key, value in extra_env_vars.items():
            if value is not None:
                extra_env_vars[key] = str(value)

        deprecated_conditional(
            lambda: "test_platform" in kwargs,
            "1.28.0.dev0",
            "test_platform",
            "Replaced with runtime_platform.",
        )
        if "test_platform" in kwargs and runtime_platform:
            raise TargetDefinitionException(
                self, "Cannot specify runtime_platform and test_platform together."
            )
        if "test_platform" in kwargs and "runtime_platform" not in kwargs:
            kwargs["runtime_platform"] = kwargs["test_platform"]
            del kwargs["test_platform"]

        payload.add_fields(
            {
                # TODO(zundel): Do extra_jvm_options and extra_env_vars really need to be fingerprinted?
                "extra_jvm_options": PrimitiveField(tuple(extra_jvm_options or ())),
                "extra_env_vars": PrimitiveField(tuple(extra_env_vars.items())),
            }
        )
        super().__init__(payload=payload, runtime_platform=runtime_platform, **kwargs)

        # These parameters don't need to go into the fingerprint:
        self._concurrency = concurrency
        self._cwd = cwd
        self._threads = None
        self._timeout = timeout

        try:
            if threads is not None:
                self._threads = int(threads)
        except ValueError:
            raise TargetDefinitionException(
                self, "The value for 'threads' must be an integer, got " + threads
            )
        if concurrency and concurrency not in self.VALID_CONCURRENCY_OPTS:
            raise TargetDefinitionException(
                self,
                "The value for 'concurrency' must be one of "
                + repr(self.VALID_CONCURRENCY_OPTS)
                + " got: "
                + concurrency,
            )

    @classmethod
    def compute_dependency_address_specs(cls, kwargs=None, payload=None):
        for address_spec in super().compute_dependency_address_specs(kwargs, payload):
            yield address_spec

        for address_spec in JUnit.global_instance().injectables_address_specs_for_key("library"):
            yield address_spec

    @property
    def test_platform(self):
        return self._test_platform()

    # NB: Cannot annotate the property. Extracted this to enable
    # warning.
    @deprecated("1.28.0.dev0", "Use runtime_platform")
    def _test_platform(self):
        return self.runtime_platform

    @property
    def concurrency(self):
        return self._concurrency

    @property
    def cwd(self):
        return self._cwd

    @property
    def threads(self):
        return self._threads

    @property
    def timeout(self):
        return self._timeout
