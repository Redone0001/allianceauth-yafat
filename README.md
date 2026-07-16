# Alliance Auth AFAT — Another Fleet Activity Tracker<a name="alliance-auth-afat-%E2%80%94-another-fleet-activity-tracker"></a>

[![Version](https://img.shields.io/pypi/v/allianceauth-afat?label=release)](https://pypi.org/project/allianceauth-afat/)
[![License](https://img.shields.io/badge/license-GPLv3-green)](https://pypi.org/project/allianceauth-afat/)
[![Python](https://img.shields.io/pypi/pyversions/allianceauth-afat)](https://pypi.org/project/allianceauth-afat/)
[![Django](https://img.shields.io/pypi/djversions/allianceauth-afat?label=django)](https://pypi.org/project/allianceauth-afat/)
![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/ppfeufer/allianceauth-afat/master.svg)](https://results.pre-commit.ci/latest/github/ppfeufer/allianceauth-afat/master)
[![Code Style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](http://black.readthedocs.io/en/latest/)
[![Automated Checks](https://github.com/ppfeufer/allianceauth-afat/actions/workflows/automated-checks.yml/badge.svg)](https://github.com/ppfeufer/allianceauth-afat/actions/workflows/automated-checks.yml)
[![codecov](https://codecov.io/gh/ppfeufer/allianceauth-afat/branch/master/graph/badge.svg?token=GNE88NUAKK)](https://codecov.io/gh/ppfeufer/allianceauth-afat)
[![Translation status](https://weblate.ppfeufer.de/widget/alliance-auth-apps/allianceauth-afat/svg-badge.svg)](https://weblate.ppfeufer.de/engage/alliance-auth-apps/)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](https://github.com/ppfeufer/allianceauth-afat/blob/master/CODE_OF_CONDUCT.md)
[![Discord](https://img.shields.io/discord/399006117012832262?label=discord)](https://discord.gg/fjnHAmk)
[![Alliance Auth Compatibility](https://img.shields.io/badge/Alliance_Auth-v5-brightgreen)](https://gitlab.com/allianceauth/allianceauth)

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/N4N8CL1BY)

An Improved FAT/PAP System for
[Alliance Auth](https://gitlab.com/allianceauth/allianceauth).

______________________________________________________________________

<!-- mdformat-toc start --slug=github --maxlevel=6 --minlevel=2 -->

- [Features and Highlights](#features-and-highlights)
- [Screenshots](#screenshots)
  - [Dashboard](#dashboard)
  - [Fat Link List](#fat-link-list)
  - [Fat Link Details](#fat-link-details)
  - [Add Fat Link View for FCs](#add-fat-link-view-for-fcs)
  - [Smart Filter: FATs in Time Period](#smart-filter-fats-in-time-period)
- [Installation](#installation)
  - [Bare Metal Installation](#bare-metal-installation)
    - [Step 1: Install the App](#step-1-install-the-app)
    - [Step 2: Update Your AA Settings](#step-2-update-your-aa-settings)
    - [Step 3: Finalizing the Installation](#step-3-finalizing-the-installation)
  - [Docker Installation](#docker-installation)
    - [Step 1: Add the App](#step-1-add-the-app)
    - [Step 2: Update Your AA Settings](#step-2-update-your-aa-settings-1)
    - [Step 3: Build Auth and Restart Your Containers](#step-3-build-auth-and-restart-your-containers)
    - [Step 4: Finalizing the Installation](#step-4-finalizing-the-installation)
- [Updating](#updating)
  - [Bare Metal Installation](#bare-metal-installation-1)
  - [Docker Installation](#docker-installation-1)
  - [Common Steps](#common-steps)
- [Data Migration](#data-migration)
  - [Import From Native FAT](#import-from-native-fat)
    - [Bare Metal Installation](#bare-metal-installation-2)
    - [Docker Installation](#docker-installation-2)
- [Settings](#settings)
- [Permissions](#permissions)
- [Changelog](#changelog)
- [Translation Status](#translation-status)
- [Contributing](#contributing)
- [Credits](#credits)

<!-- mdformat-toc end -->

______________________________________________________________________

## Features and Highlights<a name="features-and-highlights"></a>

- Automatic tracking of participation on FAT links created via ESI
- Multiple ESI fleets (with your alts)
- Manually end ESI tracking per fleet
- Fleet type classification (can be added in the admin backend)
- Ship type overview per FAT link
- Graphical statistics views
- Re-open FAT link if the FAT link has expired and is within the defined grace time
  (only for clickable FAT links)
- Manually add pilots to clickable FAT links, in case they missed clicking the link
  (for a period of 24 hours after the FAT links original expiry time)
- Log for the following actions (Logs are kept for a certain time, 60 days per default):
  - Create FAT link
  - Change FAT link
  - Remove FAT link
  - Re-open FAT link
  - Manually add pilot to FAT link
  - Remove pilot from FAT link
- Smart filter for integration with [Secure Groups](https://github.com/Solar-Helix-Independent-Transport/allianceauth-secure-groups)
  - FATs in time period

AFAT will work alongside the built-in native FAT System and ImicusFAT.
However, data doesn't share, but you can migrate their data to AFAT, for more
information, see below.

## Screenshots<a name="screenshots"></a>

### Dashboard<a name="dashboard"></a>

![Dashboard](https://raw.githubusercontent.com/ppfeufer/allianceauth-afat/master/docs/images/afat-dashboard.png "Dashboard")

### Fat Link List<a name="fat-link-list"></a>

![Fat Link List](https://raw.githubusercontent.com/ppfeufer/allianceauth-afat/master/docs/images/fatlink-list.png "Fat Link List")

### Fat Link Details<a name="fat-link-details"></a>

![Fat Link Details](https://raw.githubusercontent.com/ppfeufer/allianceauth-afat/master/docs/images/changelog/1.9.0/ship-type-overview.png "Fat Link Details")

### Add Fat Link View for FCs<a name="add-fat-link-view-for-fcs"></a>

![Add Fat Link View for FCs](https://raw.githubusercontent.com/ppfeufer/allianceauth-afat/master/docs/images/add-fatlink.png "Add Fat Link View for FCs")

### Smart Filter: FATs in Time Period<a name="smart-filter-fats-in-time-period"></a>

![Smart Filter: FATs in Time Period](https://raw.githubusercontent.com/ppfeufer/allianceauth-afat/master/docs/images/smart-filter-fats-in-time.png "Smart Filter: FATs in Time Period")

## Installation<a name="installation"></a>

> [!Important]
>
> This app is a plugin for [Alliance Auth](https://gitlab.com/allianceauth/allianceauth). \
> If you don't have Alliance Auth running already, please install it first before
> proceeding. (See the official [AA installation guide](https://allianceauth.readthedocs.io/en/latest/installation/allianceauth.html) for details)

> [!IMPORTANT]
>
> This app is utilising features that are only available in Alliance Auth >= 4.12.0.
> Please make sure to update your Alliance Auth instance before installing this app,
> otherwise, an update to Alliance Auth will be pulled in unsupervised.

> [!NOTE]
>
> For users migrating from Alliance Auth's built-in FAT systems,
> please read the [specific instructions](#data-migration).

### Bare Metal Installation<a name="bare-metal-installation"></a>

#### Step 1: Install the App<a name="step-1-install-the-app"></a>

Make sure you're in the virtual environment (venv) of your Alliance Auth installation.
Then install the latest version:

```shell
pip install allianceauth-afat==6.1.1
```

#### Step 2: Update Your AA Settings<a name="step-2-update-your-aa-settings"></a>

Configure your AA settings in your `local.py` as follows:

- Modify `INSTALLED_APPS` to include the following entries

  ```python
  INSTALLED_APPS += [
      # ...
      "eve_sde",  # Only if not already added for another app
      "afat",
      # ...
  ]

  # This line right below the `INSTALLED_APPS` list, and only if not already added for another app
  INSTALLED_APPS = ["modeltranslation"] + INSTALLED_APPS
  ```

- Add the Scheduled Tasks

  ```python
  # AFAT - https://github.com/ppfeufer/allianceauth-afat
  if "afat" in INSTALLED_APPS:
      CELERYBEAT_SCHEDULE["afat_update_esi_fatlinks"] = {
          "task": "afat.tasks.update_esi_fatlinks",
          "schedule": crontab(minute="*/1"),
      }

      CELERYBEAT_SCHEDULE["afat_auto_detect_esi_fatlinks"] = {
          "task": "afat.tasks.auto_detect_esi_fatlinks",
          "schedule": crontab(minute="*/1"),
      }

      CELERYBEAT_SCHEDULE["afat_logrotate"] = {
          "task": "afat.tasks.logrotate",
          "schedule": crontab(minute="0", hour="1"),
      }

  if "eve_sde" in INSTALLED_APPS:
      # Run at 12:00 each day
      CELERYBEAT_SCHEDULE["EVE SDE :: Check for SDE Updates"] = {
          "task": "eve_sde.tasks.check_for_sde_updates",
          "schedule": crontab(minute="0", hour="12"),
      }

      # Set the following when you have a bare metal installation, or Docker with a
      # non-standard storage for `myauth`
      ESDE_TASK_SPLIT = True
  ```

#### Step 3: Finalizing the Installation<a name="step-3-finalizing-the-installation"></a>

Run migrations, copy static files and load EVE SDE data

```shell
python manage.py collectstatic
python manage.py migrate
python manage.py esde_load_sde
```

### Docker Installation<a name="docker-installation"></a>

#### Step 1: Add the App<a name="step-1-add-the-app"></a>

Add the app to your `conf/requirements.txt`:

```text
allianceauth-afat==6.1.1
```

#### Step 2: Update Your AA Settings<a name="step-2-update-your-aa-settings-1"></a>

Configure your AA settings (`conf/local.py`) as follows:

- Modify `INSTALLED_APPS` to include the following entries

  ```python
  INSTALLED_APPS += [
      # ...
      "eve_sde",  # Only if not already added for another app
      "afat",
      # ...
  ]

  # This line right below the `INSTALLED_APPS` list, and only if not already added for another app
  INSTALLED_APPS = ["modeltranslation"] + INSTALLED_APPS
  ```

- Add the Scheduled Tasks

  ```python
  # AFAT - https://github.com/ppfeufer/allianceauth-afat
  if "afat" in INSTALLED_APPS:
      CELERYBEAT_SCHEDULE["afat_update_esi_fatlinks"] = {
          "task": "afat.tasks.update_esi_fatlinks",
          "schedule": crontab(minute="*/1"),
      }

      CELERYBEAT_SCHEDULE["afat_auto_detect_esi_fatlinks"] = {
          "task": "afat.tasks.auto_detect_esi_fatlinks",
          "schedule": crontab(minute="*/1"),
      }

      CELERYBEAT_SCHEDULE["afat_logrotate"] = {
          "task": "afat.tasks.logrotate",
          "schedule": crontab(minute="0", hour="1"),
      }

  if "eve_sde" in INSTALLED_APPS:
      # Run at 12:00 each day
      CELERYBEAT_SCHEDULE["EVE SDE :: Check for SDE Updates"] = {
          "task": "eve_sde.tasks.check_for_sde_updates",
          "schedule": crontab(minute="0", hour="12"),
      }

      # Set the following when you have a bare metal installation, or Docker with a
      # non-standard storage for `myauth`
      ESDE_TASK_SPLIT = True
  ```

#### Step 3: Build Auth and Restart Your Containers<a name="step-3-build-auth-and-restart-your-containers"></a>

```shell
docker compose build --no-cache
docker compose --env-file=.env up -d
```

#### Step 4: Finalizing the Installation<a name="step-4-finalizing-the-installation"></a>

Run migrations, copy static files and load EVE SDE data:

```shell
docker compose exec allianceauth_gunicorn bash

auth collectstatic
auth migrate
auth esde_load_sde
```

## Updating<a name="updating"></a>

### Bare Metal Installation<a name="bare-metal-installation-1"></a>

To update your existing installation of AFAT, first enable your
virtual environment (venv) of your Alliance Auth installation.

```shell
pip install allianceauth-afat==6.1.1

python manage.py collectstatic
python manage.py migrate

redis-cli flushall
```

Finally, restart your supervisor services for AA

### Docker Installation<a name="docker-installation-1"></a>

To update your existing installation of AFAT, all you need to do is to update the
respective line in your `conf/requirements.txt` file to the latest version.

```text
allianceauth-afat==6.1.1
```

Now rebuild your containers:

```shell
docker compose build
docker compose --env-file=.env up -d
```

After that, run the following commands to update your database and static files:

```shell
docker compose exec allianceauth_gunicorn bash

auth collectstatic
auth migrate
```

### Common Steps<a name="common-steps"></a>

It is possible that some versions need some more changes. Always read the
[release notes](https://github.com/ppfeufer/allianceauth-afat/releases) to find out more.

## Data Migration<a name="data-migration"></a>

Right after the **initial** installation and running migrations,
you can import the data from Alliance Auth's native FAT system if
you have used it until now.

### Import From Native FAT<a name="import-from-native-fat"></a>

To import from the native FAT module, run the following:

#### Bare Metal Installation<a name="bare-metal-installation-2"></a>

```shell
python myauth/manage.py afat_import_from_allianceauth_fat
```

#### Docker Installation<a name="docker-installation-2"></a>

```shell
docker compose exec allianceauth_gunicorn bash

auth afat_import_from_allianceauth_fat
```

## Settings<a name="settings"></a>

To customize the module, the following settings can be managed in your admin backend:

| Setting                            | Description                                                                                                                                                                                                           | Default Value |
| :--------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------ |
| Use doctrines from fittings module | Whether to use the doctrines from the Fittings modules in the doctrine dropdown or from AFATs own doctrine list. (Note: The [fittings module](https://gitlab.com/colcrunch/fittings) needs to be installed for this.) | No            |
| Default FAT link expiry time       | Default expiry time for clickable FAT links in Minutes                                                                                                                                                                | 60            |
| Default FAT link reopen grace time | Time in minutes a FAT link can be re-opened after it has expired                                                                                                                                                      | 60            |
| Default FAT link reopen duration   | Time in minutes a FAT link is re-opened                                                                                                                                                                               | 60            |
| Default log duration               | Time in days before log entries are being removed from the DB                                                                                                                                                         | 60            |

## Permissions<a name="permissions"></a>

| Name                    | Description                              | Notes                                                                                                                                                                           |
| :---------------------- | :--------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| basic_access            | Can access the AFAT module               | Your line member probably want this permission, so they can see the module and click the FAT links they are given. They also can see their own statistics with this permission. |
| manage_afat             | Can manage the AFAT module               | Your Military lead probably should get this permission                                                                                                                          |
| add_fatlink             | Can create FAT Links                     | Your regular FC or who ever should be able to add FAT links should have this permission                                                                                         |
| stats_corporation_own   | Can see own corporation statistics       |                                                                                                                                                                                 |
| stats_corporation_other | Can see statistics of other corporations |                                                                                                                                                                                 |
| logs_view               | Can view the modules logs                |                                                                                                                                                                                 |

## Changelog<a name="changelog"></a>

To keep track of all changes, please read the
[Changelog](https://github.com/ppfeufer/allianceauth-afat/blob/master/CHANGELOG.md).

## Translation Status<a name="translation-status"></a>

[![Translation status](https://weblate.ppfeufer.de/widget/alliance-auth-apps/allianceauth-afat/matrix-auto.svg)](https://weblate.ppfeufer.de/engage/alliance-auth-apps/)

Do you want to help translate this app into your language or improve the existing
translation? - [Join our team of translators][weblate engage]!

## Contributing<a name="contributing"></a>

You want to contribute to this project? That's cool!

Please make sure to read the [contribution guidelines](https://github.com/ppfeufer/allianceauth-afat/blob/master/CONTRIBUTING.md).\
(I promise, it's not much, just some basics)

## Credits<a name="credits"></a>

AFAT is maintained by @ppfeufer and is based on
[ImicusFAT](https://gitlab.com/evictus.iou/allianceauth-imicusfat)
by @exiom with @Aproia and @ppfeufer which is based on
[allianceauth-bfat](https://gitlab.com/colcrunch/allianceauth-bfat) by @colcrunch

Both of these modules are no longer maintained and are deprecated. Both modules will
not run with the latest stable releases of Alliance Auth.

<!-- Inline Links -->

[weblate engage]: https://weblate.ppfeufer.de/engage/alliance-auth-apps/ "Weblate Translations"
