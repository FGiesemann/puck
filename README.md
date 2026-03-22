# Puck - A build manager for modular C++-Projects using Conan and CMake

Puck orchestrates the setup and build of modular projects that consist of
multiple subprojects, each in their own repositories.

Projects and their dependencies are defined in a puck workspace, which is shared
between team members for example. Build configurations, i.e. conan profiles are
defined locally for each developer or machine.

Puck combines these pieces of information and orchestrates the execution of
conan and the build-tool (currently only cmake).

## Puck Workspace

The puck workspace is a folder containing a puck-workspace.json file. Usually,
the sumprojects can also be found in this directory. The puck-workspace.json
defines which subprojects are part of the workspace.

Here is an example of a workspace file that demonstrates the different
parameters:

```json
{
  "projects": [
    {
      "name": "ProjectA",
      "repository_url": "https://github.com/.../ProjectA.git",
      "conan_editable": true
    },
    {
      "name": "ProjectB",
      "repository_url": "https://github.com/.../ProjectB.git",
      "dedpends_on": [
        "ProjectA"
      ]
    },
    {
      "name": "ProjectC",
      "repository_url": "https://github.com/.../ProjectC.git",
      "no_code": true
    }
  ]
}
```

This workspace defines projects and gives their repository URLs. Project B
defines a dependency on Project A, which means, puck will build Project A before
starting the build of Project B.

In addition, Project A is defined as "conan_editable", which allows Project B to
use Project A directly without generating a conan package for Project A after
after every edit.

Project C is defined as "no_code", which means that the conan and cmake stps are
skipped for that project. (E.g. Documentation or something)

## Build Configuration

The build configuration, i.e., the conan profiles to use, are local settings
depending on the machine where the project is built.

In the workspace folder, the configuration is decribed in a puck-build.json.

Example build config:

```json
{
  "profiles": [
    {
      "name": "msvc-release",
      "description": "Build with MSVC in Release configuration",
      "conan": {
        "profile_name": "msvc195",
        "settings": {
          "compiler.cppstd": "23",
          "build_type": "Release"
        }
      },
      "build": {
        "tool": "cmake",
        "config": "conan-msvc-release"
      }
    }
  ]
}
```

Each build profile has a name, for identification. Then it is connected with a
conan profile and some additional settings that are used during the conan
install step.

The profile also defines the build tool, here cmake, and the configuration
preset to use in different cmake runs.

### Global Build Configurations

As the build configurations might be machine dependent, they can be defined
globally so that they can be reused in different projects.

The global definitons are stored in `~/.puck/puck-build.json` and are the same
as described above.

When build configurations are defined globally, the local puck-build.json can
reference them via their names:

```json
{
  "profiles": [
    "msvc-release"
  ]
}
```

### Overwriting Build Profile Settings

The globally defined build configurations can be modified in the workspace
puck-build.json:

```json
{
  "profiles": [
    {
      "name": "local-name",
      "inherits_from": "msvc-release",
      "conan": {
        "settings": {
          "compiler.cppstd": 17
        }
      }
    }
  ]
}
```

This takes all parameters from the globally defined msvc-release configuration
and overwrites the C++-Standard version.

### Skipping Builds Locally

```json
{
  "profiles": [ ... ],
  "skip_build": [
    "ProjectB"
  ]
}
```

The build for some projects may be skipped locally. This will not skip the conan
install step for this project.

## Puck Commands

After creating the global puck-build.json, a projekt managed with puck can be
used like this:

1. Get the puck workspace, e.g. by cloning it
2. In the workspace, where the puck-workspace.json is, add a puck-build.json
   listing the build configurations you want to use for the subprojects

Then, a sequence of puck command can be used as follows:

1. `setup` to clone or update the subprojects
2. `install` to install the conan dependencies
3. `build` to build the subprojects
4. `check` to check the build configurations

### Setup

```sh
puck setup [--clean]
```

This clones all subprojects listed in the puck-workspace.json, if a repository
url is given.

If the subproject already exists, setup tries to update the projects to the
remote repository state. This might not be possible due to local changes, unless
the --clean option is given. In that case, **the project is cleaned
aggressively, risking loss of local changes**.

### Installing

```sh
puck install
```

Runs conan install for each subproject with each selected build configuration.

### Building

```sh
puck build [profiles="..."] [--target cmake_target]
```

This runs a build of the subprojects in an order that respects dependencies
between them. A list of build configurations can be specified and also the
cmake target to build (default is all).

### Checking

```sh
puck check
```

Checks the configurations, resolves local and global build configurations and
prints the order in which subprojects will be built.
