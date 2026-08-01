from __future__ import annotations

import importlib


def test_integrations_package_lazy_loads_telegram_without_cycle() -> None:
    """Importing WatchdogAdapter must not require a fully initialized orchestrator."""
    import services.integrations as integrations
    import services.orchestrator.capabilities as capabilities

    importlib.reload(integrations)
    assert hasattr(integrations, "WatchdogAdapter")
    assert callable(capabilities.plan_actions_for_goal)


def test_capabilities_import_does_not_raise_circular_error() -> None:
    from services.orchestrator.capabilities import plan_actions_for_goal

    actions = plan_actions_for_goal("say hello")
    assert actions


def test_integrations_getattr_exposes_telegram_symbols() -> None:
    import services.integrations as integrations

    assert integrations.TelegramBotService.__name__ == "TelegramBotService"
    assert callable(integrations.run_telegram_bot_forever)
    raised = False
    try:
        _ = integrations.DoesNotExist
    except AttributeError:
        raised = True
    assert raised is True
