def test_cli_happy_path(monkeypatch, reload_modules, main_module, tmp_path):
    journal = reload_modules["journal"]
    configuration = reload_modules["solace.configuration"]

    export_target = tmp_path / "export.md"

    prompts = iter(
        [
            "/diary A short note",  # command prompt
            "2024-01-02",  # date prompt
            "09:00",  # time prompt
            "",  # tags prompt
            "/search note",  # command prompt
            f"/export markdown {export_target}",  # command prompt
            "exit",  # command prompt
        ]
    )

    monkeypatch.setattr(main_module.Prompt, "ask", lambda *args, **kwargs: next(prompts))

    main_module.run_cli()

    config = configuration.load_config()
    cipher = configuration.get_cipher(config, password="seed-password")

    entries = journal.load_entries(cipher=cipher)
    assert entries
    assert entries[0].content == "A short note"

    exported = export_target
    assert exported.exists()
    content = exported.read_text(encoding="utf-8")
    assert "A short note" in content
