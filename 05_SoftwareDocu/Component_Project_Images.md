# Component: Project images and external preparation

## Purpose and responsibilities

Administrators select a backend, runtime and available executor image during
enrollment and reviewed Settings edits. Project-specific image preparation/building
is an operator action. ADORE retains reviewed source recipes for export and binds
actual run container/image identity; registration does not build or resume jobs.

The environment selector lists images installed on the server's chosen runtime.
Native projects use managed Pi instead of a container image. Optional preparation
recipes can determine the effective image before a job is admitted.
See [Executor recipes](Component_Executor_Recipes.md),
[Preparation](Component_Preparation.md) and [Execution](Component_Execution.md).

## Configuration and export boundaries

The reviewed pending flow accepts backend, runtime, image, package permission,
Git build definition and local tools PATH. The native account is current;
server process delegation is not a project-editable home/cgroup selection. Other environment settings remain operator
configuration; unsupported web candidates receive environment_managed_externally.
Pending records have a single closed current schema. Unknown bindings/unsupported
keys are refused as pending_config_corrupt; an administrator may discard the
pending candidate explicitly. No earlier binding is read or converted.

The compact export dialog retains Dockerfile/context sources by image and supplies
the standard base recipe where needed. Source selection is independent of the
runtime used to build it. Export resolves a closed dependency graph and returns
exact reviewed sources; it does not call the container build command.
See [Build bundles](Component_Build_Bundle.md).

Project-specific builds are external. Shared base/proxy prerequisites have their
own explicit setup/readiness preparation boundary; this does not add a general
project-image build service. Local profiles omit container build guidance.

## ADORE repository executor recipe

`02_Tools/build/executor_images/adore/` contains this repository's operator-owned
Dockerfile, Docker ignore rules, schema-1 build.json manifest and build instructions.
The recipe declares the Python/web/browser toolchain and uses the repository root
as build context with a reviewed input allowlist. It runs as the configured
non-root image user. Runtime dependency pins belong to these source files.

The build manifest binds exact image, Dockerfile and regular context files to a
full Git commit through container.build_definition. Registration/export reads
those immutable bytes; an operator builds/checks the image separately and selects
it for the project. Registration and source export do not modify the recipe or launch its build. See the [recipe README](../02_Tools/build/executor_images/adore/README.md)
for commands instead of maintaining a second recipe manual here.

## Dependencies and validation coverage

Profile/configuration services own selection; the web runtime inventory supplies
suggestions; ContainerBackend owns actual immutable runtime identity. Recipe
storage and Git bundle readers own the source trust boundaries. No separate
image-build operation/store is part of this component.

Existing `04_Software/tests/test_executor_environment_choice.py`,
`test_web_pending_config.py` and `04_Software/web/e2e/images.spec.ts` cover selection,
external-only fields and pending-record refusal. See
[Project executor images](../01_Documentation/Project_Executor_Images.md) for the
operator workflow. Secrets and installed runtime images are not source-bundle data.
