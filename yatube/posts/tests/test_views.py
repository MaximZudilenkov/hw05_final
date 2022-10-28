
from django import forms
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Comment, Follow, Group, Post, User


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.not_author_user = User.objects.create_user(username='HasNoName')
        cls.another_user = User.objects.create_user(username='another_user')

        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='group-slug',
            description='Тестовое описание',
        )

        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif')

        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=Group.objects.get(title='Тестовая группа'),
            image=uploaded
        )

        cls.follow = Follow.objects.create(
            user=cls.not_author_user,
            author=cls.user
        )

        cls.comment = Comment.objects.create(
            author=cls.user,
            text='Тестовый комментарий',
            post=cls.post
        )

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_author_client = Client()
        self.authorized_another_user_client = Client()
        self.authorized_client.force_login(self.not_author_user)
        self.authorized_author_client.force_login(self.user)
        self.authorized_another_user_client.force_login(self.another_user)

    def check_context(self, url, post, **kwargs):
        """Метод, проверяющий переданный в шаблоны контекст"""
        response = self.authorized_client.get(reverse(url, **kwargs))
        if post == 'page_obj':
            first_object = response.context[post][0]
        else:
            first_object = response.context[post]
        return (
            self.assertEqual(
                first_object.text, self.post.text), self.assertEqual(
                first_object.author, self.user), self.assertEqual(
                first_object.group, self.group)), self.assertEqual(
            first_object.image, self.post.image)

    def check_group_in_posts(self, url, **kwargs):
        """Метод, проверяющий группу у постов в шаблонах"""
        response = self.guest_client.get(reverse(url, **kwargs))
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.group, self.group)

    def test_pages_uses_correct_template(self):
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list',
                    kwargs={'slug': 'group-slug'}): 'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username': self.user.username}):
            'posts/profile.html',
            reverse('posts:post_detail',
                    kwargs={'post_id': self.post.pk}):
            'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create.html',
            reverse(
                'posts:post_edit', kwargs={'post_id': self.post.pk}):
            'posts/create.html',

        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_author_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        self.check_context('posts:index', 'page_obj')

    def test_group_list_page_show_correct_context(self):
        self.check_context('posts:group_list',
                           'page_obj', kwargs={'slug': 'group-slug'}, )
        response = self.authorized_client.get(reverse
                                              ('posts:group_list',
                                               kwargs={'slug': 'group-slug'}))
        self.assertEqual(response.context['group'].title, self.group.title)
        self.assertEqual(response.context['group'].slug, self.group.slug)
        self.assertEqual(response.context['group'].description,
                         self.group.description)

    def test_profile_page_show_correct_context(self):
        self.check_context('posts:profile', 'page_obj',
                           kwargs={'username': self.user.username})
        response = (self.authorized_client.get
                    (reverse('posts:profile',
                             kwargs={'username': self.user.username})))
        self.assertEqual(response.context['author'],
                         self.user)
        self.assertEqual(response.context['posts'].count(),
                         self.user.posts.count())

    def test_post_detail_page_show_correct_context(self):
        self.check_context('posts:post_detail',
                           'post', kwargs={'post_id': self.post.pk})

    def test_create_page_show_correct_context(self):
        response = self.authorized_client.get(reverse('posts:post_create', ))
        self.assertTrue(response.context['form'])
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField, }

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_create_page_for_edit_show_correct_context(self):
        self.authorized_author_client.force_login(self.user)
        response = (self.authorized_author_client.get
                    (reverse('posts:post_edit',
                             kwargs={'post_id': self.post.pk})))
        self.assertTrue(response.context['form'])
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField, }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)
        self.assertEqual(response.context.get('is_edit'), True)

    def test_post_with_group_at_index_page(self):
        self.check_group_in_posts('posts:index')
        self.check_group_in_posts('posts:group_list',
                                  kwargs={'slug': 'group-slug'})
        self.check_group_in_posts('posts:profile',
                                  kwargs={'username': self.user.username})

    def test_comment_in_post_detail_page(self):
        response = self.authorized_client.get(
            reverse(
                'posts:post_detail', kwargs={
                    'post_id': self.post.pk}))
        self.assertEqual(
            response.context['comments'][0].text,
            self.comment.text)
        self.assertEqual(response.context['comments'][0].author, self.user)
        self.assertEqual(response.context['comments'][0].post, self.post)

    def test_cache_at_index_page(self):
        cache.clear()
        response_old = self.guest_client.get(reverse('posts:index'))
        Post.objects.create(
            author=self.user,
            text='Кеш пост ')
        response_new = self.guest_client.get(reverse('posts:index'))
        self.assertEqual(response_old.content, response_new.content)
        cache.clear()
        response_new = self.guest_client.get(reverse('posts:index'))
        self.assertNotEqual(response_old.content, response_new.content)

    def test_profile_follow(self):
        self.assertEqual(Follow.objects.first(), self.follow)

    def test_profile_unfollow(self):
        follow = Follow.objects.filter(
            user=self.not_author_user, author=self.user)
        self.assertTrue(follow.exists())
        (self.authorized_client.get
         (reverse('posts:profile_unfollow',
                  kwargs={'username': self.user.username})))
        self.assertFalse(follow.exists())

    def test_context_for_followers_and_not_followers(self):
        response_follower = self.authorized_client.get(
            reverse('posts:follow_index'))
        response_not_follower = self.authorized_another_user_client.get(
            reverse('posts:follow_index'))
        self.assertIn(self.post,
                      response_follower.context['page_obj'].object_list)
        self.assertNotIn(self.post,
                         response_not_follower.context['page_obj'].object_list)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='group-slug',
            description='Тестовое описание',
        )
        cls.post = [Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=Group.objects.get(title='Тестовая группа'))
            for i in range(13)]

    def setUp(self):
        self.guest_client = Client()

    def records_on_two_pages(self, url, **kwargs):
        response_page_one = self.client.get(reverse(url, **kwargs))
        response_page_two = self.client.get(reverse(url, **kwargs) + '?page=2')
        self.assertEqual(len(response_page_one.context['page_obj']), 10)
        self.assertEqual(len(response_page_two.context['page_obj']), 3)

    def test_pages_contains_records(self):
        self.records_on_two_pages('posts:index')
        self.records_on_two_pages('posts:group_list',
                                  kwargs={'slug': 'group-slug'})
        self.records_on_two_pages('posts:profile',
                                  kwargs={'username': self.user.username})
