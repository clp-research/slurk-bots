from taboo.__main__ import TabooBot


class TestTabooBot:
    def test_init(self):
        assert TabooBot('token', 'user', 'task', 'host', 5000)


    def test_register_callbacks(self):
        bot = TabooBot('token', 'user', 'task', 'host', 5000)
        # bot.register_callbacks

