from http import HTTPStatus

from django.test import Client, TestCase

from ..models import Group, Post, User


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.not_author_user = User.objects.create_user(username='HasNoName')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='group-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )
        cls.public_urls = ['/', '/group/group-slug/',
                           f'/profile/{cls.user.username}/',
                           f'/posts/{cls.post.pk}/']
        cls.private_urls = ['/create/', ]
        cls.author_private_urls = [f'/posts/'f'{cls.post.pk}/edit/']

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_author_client = Client()
        self.authorized_client.force_login(self.not_author_user)
        self.authorized_author_client.force_login(self.user)

    def test_public_urls(self):
        for url in self.public_urls:
            with self.subTest(field=url):
                self.assertEqual(self.guest_client.get
                                 (url).status_code, HTTPStatus.OK)

    def test_private_urls_for_unlogged_users(self):
        for url in self.private_urls:
            with self.subTest(field=url):
                self.assertEqual(self.guest_client.get
                                 (url).status_code, HTTPStatus.FOUND)
                self.assertRedirects(self.guest_client.get
                                     (url), '/auth/login/?next=/create/')

    def test_private_and_public_urls_for_logged_users(self):
        for url in (self.public_urls + self.private_urls):
            with self.subTest(field=url):
                self.assertEqual(self.authorized_client.get
                                 (url).status_code, HTTPStatus.OK)

    def test_author_private_urls_for_logged_users(self):
        for url in self.author_private_urls:
            with self.subTest(field=url):
                self.assertEqual(self.authorized_client.get
                                 (url).status_code, HTTPStatus.FOUND)
                self.assertRedirects(
                    self.guest_client.get(url),
                    '/auth/login/?next=%2Fposts%2F1%2Fedit%2F')

    def test_urls_uses_correct_template(self):
        templates_url_names = {
            '/': 'posts/index.html',
            '/group/group-slug/': 'posts/group_list.html',
            f'/profile/{self.user.username}/': 'posts/profile.html',
            f'/posts/{self.post.pk}/': 'posts/post_detail.html',
            '/create/': 'posts/create.html',
            f'/posts/{self.post.pk}/edit/': 'posts/create.html',
            '/not_exists_page/': 'core/404.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_author_client.get(address)
                self.assertTemplateUsed(response, template)
