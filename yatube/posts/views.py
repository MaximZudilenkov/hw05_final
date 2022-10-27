
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_page

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post, User

posts_in_page = 10



def index(request):
    template = 'posts/index.html'
    posts = Post.objects.all()
    paginator = Paginator(posts, posts_in_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {'page_obj': page_obj}
    return render(request, template, context)


def group_list(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()
    paginator = Paginator(posts, posts_in_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    template = 'posts/group_list.html'
    context = {'group': group, 'page_obj': page_obj
               }
    return render(request, template, context)


def profile(request, username):
    author = User.objects.get(username=username)
    if request.user.is_authenticated:
        following = author in [
            post.author for post in request.user.follower.all()]
    else:
        following = None
    posts_from_author = author.posts.all()
    paginator = Paginator(posts_from_author, posts_in_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {'posts': posts_from_author, 'author': author,
               'count': author.posts.all().count(), 'page_obj': page_obj,
               'following': following}
    return render(request, 'posts/profile.html', context)


@login_required
def add_comment(request, post_id):
    post = Post.objects.get(pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


def post_detail(request, post_id):
    form = CommentForm()
    post = Post.objects.get(pk=post_id)
    author = User.objects.get(pk=post.author_id)
    comments = post.comments.all()
    context = {
        'post': post,
        'count': author.posts.all().count(),
        'form': form,
        'comments': comments}
    return render(request, 'posts/post_detail.html', context)


@login_required()
def post_create(request):
    if request.method == 'POST':
        form = PostForm(
            request.POST or None,
            initial={
                'author': request.user},
            files=request.FILES or None)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            form.save()
            return redirect('posts:profile', post.author.username)
    else:
        form = PostForm(initial={'author': request.user})
    context = {'form': form, }
    return render(request, 'posts/create.html', context)


@login_required()
def post_edit(request, post_id):
    post = Post.objects.get(pk=post_id)
    is_edit = True
    if post.author != request.user:
        return redirect('users:login')
    else:
        if request.method == 'POST':
            form = PostForm(
                request.POST or None,
                files=request.FILES or None,
                instance=post
            )
            if form.is_valid():
                form.save()
                return redirect('posts:post_detail', post.pk)
        else:
            form = PostForm(instance=post)
        context = {'form': form, 'is_edit': is_edit}
        return render(request, 'posts/create.html', context)


@login_required
def follow_index(request):
    authors = [post.author for post in request.user.follower.all()]
    posts = Post.objects.filter(author__in=authors)
    paginator = Paginator(posts, posts_in_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {'page_obj': page_obj}
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    if request.user == User.objects.get(
        username=username) or Follow.objects.filter(
        author=User.objects.get(
            username=username)).exists():
        return redirect('posts:index')
    else:
        Follow.objects.update_or_create(
            user=request.user,
            author=User.objects.get(
                username=username))
    return redirect('posts:follow_index')


@login_required
def profile_unfollow(request, username):
    Follow.objects.get(
        user=request.user,
        author=User.objects.get(
            username=username)).delete()
    return redirect('posts:index')
